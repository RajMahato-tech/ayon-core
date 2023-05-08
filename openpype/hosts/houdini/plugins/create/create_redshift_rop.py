# -*- coding: utf-8 -*-
"""Creator plugin to create Redshift ROP."""
import hou  # noqa

from openpype.hosts.houdini.api import plugin
from openpype.pipeline import CreatedInstance
from openpype.lib import EnumDef


class CreateRedshiftROP(plugin.HoudiniCreator):
    """Redshift ROP"""
    identifier = "io.openpype.creators.houdini.redshift_rop"
    label = "Redshift ROP"
    family = "redshift_rop"
    icon = "magic"
    defaults = ["master"]
    ext = "exr"

    def create(self, subset_name, instance_data, pre_create_data):

        instance_data.pop("active", None)
        instance_data.update({"node_type": "Redshift_ROP"})
        # Add chunk size attribute
        instance_data["chunkSize"] = 10
        # Submit for job publishing
        instance_data["farm"] = True

        instance = super(CreateRedshiftROP, self).create(
            subset_name,
            instance_data,
            pre_create_data)  # type: CreatedInstance

        instance_node = hou.node(instance.get("instance_node"))

        basename = instance_node.name()

        # Also create the linked Redshift IPR Rop
        try:
            ipr_rop = instance_node.parent().createNode(
                "Redshift_IPR", node_name=basename + "_IPR"
            )
        except hou.OperationFailed:
            raise plugin.OpenPypeCreatorError(
                ("Cannot create Redshift node. Is Redshift "
                 "installed and enabled?"))

        # Move it to directly under the Redshift ROP
        ipr_rop.setPosition(instance_node.position() + hou.Vector2(0, -1))

        # Set the linked rop to the Redshift ROP
        ipr_rop.parm("linked_rop").set(instance_node.path())

        ext = pre_create_data.get("image_format")
        filepath = "{renders_dir}{subset_name}/{subset_name}.{fmt}".format(
            renders_dir=hou.text.expandString("$HIP/pyblish/renders/"),
                subset_name=subset_name,
                fmt="${aov}.$F4.{ext}".format(aov="AOV", ext=ext)
            )

        parms = {
            # Render frame range
            "trange": 1,
            # Redshift ROP settings
            "RS_outputFileNamePrefix": filepath,
            "RS_outputMultilayerMode": "1",  # no multi-layered exr
            "RS_outputBeautyAOVSuffix": "beauty",
        }

        if self.selected_nodes:
            # set up the render camera from the selected node
            camera = None
            for node in self.selected_nodes:
                if node.type().name() == "cam":
                    camera = node.path()
            parms.update({
                "RS_renderCamera": camera or ""})
        instance_node.setParms(parms)

        # Lock some Avalon attributes
        to_lock = ["family", "id"]
        self.lock_parameters(instance_node, to_lock)

    def remove_instances(self, instances):
        for instance in instances:
            node = instance.data.get("instance_node")

            ipr_node = hou.node(f"{node}_IPR")
            if ipr_node:
                ipr_node.destroy()

        return super(CreateRedshiftROP, self).remove_instances(instances)

    def get_pre_create_attr_defs(self):
        attrs = super(CreateRedshiftROP, self).get_pre_create_attr_defs()
        image_format_enum = [
            "bmp", "cin", "exr", "jpg", "pic", "pic.gz", "png",
            "rad", "rat", "rta", "sgi", "tga", "tif",
        ]

        return attrs + [
            EnumDef("image_format",
                    image_format_enum,
                    default=self.ext,
                    label="Image Format Options")
        ]
