# -*- coding: utf-8 -*-
"""Creator plugin to create Karma ROP."""
from ayon_core.hosts.houdini.api import plugin
from ayon_core.lib import BoolDef, EnumDef, NumberDef


class CreateKarmaROP(plugin.HoudiniCreator):
    """Karma ROP"""
    identifier = "io.openpype.creators.houdini.karma_rop"
    label = "Karma ROP"
    product_type = "karma_rop"
    icon = "magic"
    render_staging_dir = "$HIP/ayon/{product[name]}/render/{product[name]}.$F4.{ext}"
    checkpoint_dir = "$HIP/ayon/{product[name]}/checkpoint/{product[name]}.$F4.{ext}"
    usd_dir = "$HIP/ayon/{product_name}/usd/{product_name}_$RENDERID"

    def create(self, product_name, instance_data, pre_create_data):
        import hou  # noqa

        instance_data.pop("active", None)
        instance_data.update({"node_type": "karma"})
        # Add chunk size attribute
        instance_data["chunkSize"] = 10
        # Submit for job publishing
        instance_data["farm"] = pre_create_data.get("farm")

        instance = super(CreateKarmaROP, self).create(
            product_name,
            instance_data,
            pre_create_data)

        instance_node = hou.node(instance.get("instance_node"))

        ext = pre_create_data.get("image_format")

        filepath = self.render_staging_dir.format(
            product={"name": "`chs(\"AYON_productName\")`"},
            ext=ext
        )

        checkpoint = self.checkpoint_dir.format(
            product={"name": "`chs(\"AYON_productName\")`"},
            ext="checkpoint"
        )

        usd_directory = self.usd_dir.format(
            product={"name": "`chs(\"AYON_productName\")`"},
        )

        parms = {
            # Render Frame Range
            "trange": 1,
            # Karma ROP Setting
            "picture": filepath,
            # Karma Checkpoint Setting
            "productName": checkpoint,
            # USD Output Directory
            "savetodirectory": usd_directory,
        }

        res_x = pre_create_data.get("res_x")
        res_y = pre_create_data.get("res_y")

        if self.selected_nodes:
            # If camera found in selection
            # we will use as render camera
            camera = None
            for node in self.selected_nodes:
                if node.type().name() == "cam":
                    camera = node.path()
                    has_camera = pre_create_data.get("cam_res")
                    if has_camera:
                        res_x = node.evalParm("resx")
                        res_y = node.evalParm("resy")

            if not camera:
                self.log.warning("No render camera found in selection")

            parms.update({
                "camera": camera or "",
                "resolutionx": res_x,
                "resolutiony": res_y,
            })

        instance_node.setParms(parms)

        # Lock some Avalon attributes
        to_lock = ["productType", "id"]
        self.lock_parameters(instance_node, to_lock)

    def get_pre_create_attr_defs(self):
        attrs = super(CreateKarmaROP, self).get_pre_create_attr_defs()

        image_format_enum = [
            "bmp", "cin", "exr", "jpg", "pic", "pic.gz", "png",
            "rad", "rat", "rta", "sgi", "tga", "tif",
        ]

        return attrs + [
            BoolDef("farm",
                    label="Submitting to Farm",
                    default=True),
            EnumDef("image_format",
                    image_format_enum,
                    default="exr",
                    label="Image Format Options"),
            NumberDef("res_x",
                      label="width",
                      default=1920,
                      decimals=0),
            NumberDef("res_y",
                      label="height",
                      default=720,
                      decimals=0),
            BoolDef("cam_res",
                    label="Camera Resolution",
                    default=False)
        ]
