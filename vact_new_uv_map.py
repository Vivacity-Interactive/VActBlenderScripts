import bpy

class _Settings:
    def __init__(self):
        self.uv_enable = True
        self.uv_name = "UVProjection"


class VActNewUVMap:
    def do_execute(self, context, settings):
        for item in context:
            if settings.object_to_data: item.data.name = item.name
            else: item.name = item.data.name


settings = _Settings()

layer = bpy.context.view_layer
active = layer.objects.active
selection = bpy.context.selected_objects

operator = VActForceName()
operator.do_execute(selection, settings)