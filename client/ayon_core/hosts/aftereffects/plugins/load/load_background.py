import re

from ayon_core.pipeline import get_representation_path
from ayon_core.hosts.aftereffects import api

from ayon_core.hosts.aftereffects.api.lib import (
    get_background_layers,
    get_unique_layer_name,
)


class BackgroundLoader(api.AfterEffectsLoader):
    """
        Load images from Background product type
        Creates for each background separate folder with all imported images
        from background json AND automatically created composition with layers,
        each layer for separate image.

        For each load container is created and stored in project (.aep)
        metadata
    """
    label = "Load JSON Background"
    families = ["background"]
    representations = ["json"]

    def load(self, context, name=None, namespace=None, data=None):
        stub = self.get_stub()
        items = stub.get_items(comps=True)
        existing_items = [layer.name.replace(stub.LOADED_ICON, '')
                          for layer in items]

        comp_name = get_unique_layer_name(
            existing_items,
            "{}_{}".format(context["asset"]["name"], name))

        path = self.filepath_from_context(context)
        layers = get_background_layers(path)
        if not layers:
            raise ValueError("No layers found in {}".format(path))

        comp = stub.import_background(None, stub.LOADED_ICON + comp_name,
                                      layers)

        if not comp:
            raise ValueError("Import background failed. "
                             "Please contact support")

        self[:] = [comp]
        namespace = namespace or comp_name

        return api.containerise(
            name,
            namespace,
            comp,
            context,
            self.__class__.__name__
        )

    def update(self, container, context):
        """ Switch asset or change version """
        stub = self.get_stub()
        asset_doc = context["asset"]
        subset_doc = context["subset"]
        repre_doc = context["representation"]

        folder_name = asset_doc["name"]
        product_name = subset_doc["name"]
        _ = container.pop("layer")

        # without iterator number (_001, 002...)
        namespace_from_container = re.sub(r'_\d{3}$', '',
                                          container["namespace"])
        comp_name = "{}_{}".format(folder_name, product_name)

        # switching assets
        if namespace_from_container != comp_name:
            items = stub.get_items(comps=True)
            existing_items = [layer.name for layer in items]
            comp_name = get_unique_layer_name(
                existing_items,
                "{}_{}".format(folder_name, product_name))
        else:  # switching version - keep same name
            comp_name = container["namespace"]

        path = get_representation_path(repre_doc)

        layers = get_background_layers(path)
        comp = stub.reload_background(container["members"][1],
                                      stub.LOADED_ICON + comp_name,
                                      layers)

        # update container
        container["representation"] = str(repre_doc["_id"])
        container["name"] = product_name
        container["namespace"] = comp_name
        container["members"] = comp.members

        stub.imprint(comp.id, container)

    def remove(self, container):
        """
            Removes element from scene: deletes layer + removes from file
            metadata.
        Args:
            container (dict): container to be removed - used to get layer_id
        """
        stub = self.get_stub()
        layer = container.pop("layer")
        stub.imprint(layer.id, {})
        stub.delete_item(layer.id)

    def switch(self, container, context):
        self.update(container, context)
