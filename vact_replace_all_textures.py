import bpy

class _Settings:
    def __init__(self):
        self.material_name = "Default"


class VActReplaceAllTextures:
    def do_execute(self, context, settings):
        material = bpy.data.materials[settings.material_name]
        for item in context:
            if not item.type in {"MESH"}: continue
            for index in range(len(item.data.materials)): item.data.materials[index] = material


settings = _Settings()

layer = bpy.context.view_layer
active = layer.objects.active
selection = bpy.context.selected_objects

operator = VActReplaceAllTextures()
operator.do_execute(selection, settings)