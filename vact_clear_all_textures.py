import bpy

class _Settings:
    def __init__(self):
        pass


class VActClearAllTextures:
    def do_execute(self, context, settings):
        for item in context:
            if item.type in {"MESH"}: item.data.materials.clear() 


settings = _Settings()

layer = bpy.context.view_layer
active = layer.objects.active
selection = bpy.context.selected_objects

operator = VActClearAllTextures()
operator.do_execute(selection, settings)