# -*- coding: utf-8 -*-
"""Creator plugin for creating Arnold ASS files."""
from ayon_core.hosts.houdini.api import plugin
from ayon_core.lib import BoolDef


class CreateArnoldAss(plugin.HoudiniCreator):
    """Arnold .ass Archive"""

    identifier = "io.openpype.creators.houdini.ass"
    label = "Arnold ASS"
    product_type = "ass"
    icon = "magic"

    # Default extension: `.ass` or `.ass.gz`
    # however calling HoudiniCreator.create()
    # will override it by the value in the project settings
    ext = ".ass"
    staging_dir = "$HIP/ayon/{product[name]}/{product[name]}.{ext}"

    def create(self, product_name, instance_data, pre_create_data):
        import hou

        instance_data.pop("active", None)
        instance_data.update({"node_type": "arnold"})
        creator_attributes = instance_data.setdefault(
            "creator_attributes", dict())
        creator_attributes["farm"] = pre_create_data["farm"]

        instance = super(CreateArnoldAss, self).create(
            product_name,
            instance_data,
            pre_create_data)

        instance_node = hou.node(instance.get("instance_node"))

        # Hide Properties Tab on Arnold ROP since that's used
        # for rendering instead of .ass Archive Export
        parm_template_group = instance_node.parmTemplateGroup()
        parm_template_group.hideFolder("Properties", True)
        instance_node.setParmTemplateGroup(parm_template_group)

        filepath = self.staging_dir.format(
            product={"name": "`chs(\"AYON_productName\")`"},
            ext=self.ext.lstrip(".")
        )

        parms = {
            # Render frame range
            "trange": 1,
            # Arnold ROP settings
            "ar_ass_file": filepath,
            "ar_ass_export_enable": 1
        }

        instance_node.setParms(parms)

        # Lock any parameters in this list
        to_lock = ["ar_ass_export_enable", "productType", "id"]
        self.lock_parameters(instance_node, to_lock)

    def get_instance_attr_defs(self):
        return [
            BoolDef("farm",
                    label="Submitting to Farm",
                    default=False)
        ]

    def get_pre_create_attr_defs(self):
        attrs = super().get_pre_create_attr_defs()
        # Use same attributes as for instance attributes
        return attrs + self.get_instance_attr_defs()
