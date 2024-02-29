import pyblish.api

import ayon_core.hosts.maya.api.action
from ayon_core.client import get_subset_by_name
from ayon_core.pipeline.publish import PublishValidationError


class ValidateRenderLayerAOVs(pyblish.api.InstancePlugin):
    """Validate created AOVs / RenderElement is registered in the database

    Each render element is registered as a product which is formatted based on
    the render layer and the render element, example:

        <render layer>.<render element>

    This translates to something like this:

        CHAR.diffuse

    This check is needed to ensure the render output is still complete

    """

    order = pyblish.api.ValidatorOrder + 0.1
    label = "Render Passes / AOVs Are Registered"
    hosts = ["maya"]
    families = ["renderlayer"]
    actions = [ayon_core.hosts.maya.api.action.SelectInvalidAction]

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            raise PublishValidationError(
                "Found unregistered products: {}".format(invalid))

    def get_invalid(self, instance):
        invalid = []

        project_name = instance.context.data["projectName"]
        asset_doc = instance.data["assetEntity"]
        render_passes = instance.data.get("renderPasses", [])
        for render_pass in render_passes:
            is_valid = self.validate_product_registered(
                project_name, asset_doc, render_pass
            )
            if not is_valid:
                invalid.append(render_pass)

        return invalid

    def validate_product_registered(
        self, project_name, asset_doc, product_name
    ):
        """Check if product is registered in the database under the asset"""

        return get_subset_by_name(
            project_name, product_name, asset_doc["_id"], fields=["_id"]
        )
