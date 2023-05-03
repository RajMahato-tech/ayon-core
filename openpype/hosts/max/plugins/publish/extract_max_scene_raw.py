import os
import pyblish.api
from openpype.pipeline import (
    publish,
    OptionalPyblishPluginMixin
)
from pymxs import runtime as rt
from openpype.hosts.max.api import (
    maintained_selection
)


class ExtractMaxSceneRaw(publish.Extractor,
                         OptionalPyblishPluginMixin):
    """
    Extract Raw Max Scene with SaveSelected
    """

    order = pyblish.api.ExtractorOrder - 0.2
    label = "Extract Max Scene (Raw)"
    hosts = ["max"]
    families = ["camera",
                "maxScene",
                "model"]
    optional = True

    def process(self, instance):
        if not self.is_active(instance.data):
            return

        # publish the raw scene for camera
        self.log.info("Extracting Raw Max Scene ...")

        stagingdir = self.staging_dir(instance)
        filename = "{name}.max".format(**instance.data)

        max_path = os.path.join(stagingdir, filename)
        self.log.info(f"Writing max file '{filename}' to '{max_path}'")

        if "representations" not in instance.data:
            instance.data["representations"] = []

        # saving max scene
        with maintained_selection():
            # need to figure out how to select the camera
            rt.Select(instance.data["members"])
            rt.Execute(f'saveNodes selection "{max_path}" quiet:true')

        self.log.info("Performing Extraction ...")

        representation = {
            'name': 'max',
            'ext': 'max',
            'files': filename,
            "stagingDir": stagingdir,
        }
        instance.data["representations"].append(representation)
        self.log.info(f"Extracted instance '{instance.name}' to: {max_path}")
