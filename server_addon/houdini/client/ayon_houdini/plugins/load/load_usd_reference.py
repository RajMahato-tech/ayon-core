from ayon_core.pipeline import (
    load,
    get_representation_path,
    AVALON_CONTAINER_ID,
)
from ayon_houdini.api import lib


class USDReferenceLoader(load.LoaderPlugin):
    """Reference USD file in Solaris"""

    product_types = {
        "usd",
        "usdCamera",
    }
    label = "Reference USD"
    representations = {"usd", "usda", "usdlc", "usdnc", "abc"}
    order = -8

    icon = "code-fork"
    color = "orange"

    def load(self, context, name=None, namespace=None, data=None):

        import os
        import hou

        # Format file name, Houdini only wants forward slashes
        file_path = self.filepath_from_context(context)
        file_path = os.path.normpath(file_path)
        file_path = file_path.replace("\\", "/")

        # Get the root node
        stage = hou.node("/stage")

        # Define node name
        namespace = namespace if namespace else context["folder"]["name"]
        node_name = "{}_{}".format(namespace, name) if namespace else name

        # Create USD reference
        container = stage.createNode("reference", node_name=node_name)
        container.setParms({"filepath1": file_path})
        container.moveToGoodPosition()

        # Imprint it manually
        data = {
            "schema": "openpype:container-2.0",
            "id": AVALON_CONTAINER_ID,
            "name": node_name,
            "namespace": namespace,
            "loader": str(self.__class__.__name__),
            "representation": context["representation"]["id"],
        }

        # todo: add folder="Avalon"
        lib.imprint(container, data)

        return container

    def update(self, container, context):
        repre_entity = context["representation"]
        node = container["node"]

        # Update the file path
        file_path = get_representation_path(repre_entity)
        file_path = file_path.replace("\\", "/")

        # Update attributes
        node.setParms(
            {
                "filepath1": file_path,
                "representation": repre_entity["id"],
            }
        )

        # Reload files
        node.parm("reload").pressButton()

    def remove(self, container):

        node = container["node"]
        node.destroy()

    def switch(self, container, context):
        self.update(container, context)