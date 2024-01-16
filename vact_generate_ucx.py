import bpy

class _Settings:
    def __init__(self):
        self.into = "UCX"
        self.target_lod = "_LOD0"


class VActGenerateUCX:
    def do_generate(self, context, settings):
        into = bpy.data.collections[settings.into]
        
        for mesh in context:
            b_mesh = mesh.type in {'MESH'}
            if not b_mesh: continue
            
            name = mesh.name.replace(settings.target_lod,"")
            ucx = mesh.copy()
            ucx.name = "UCX_" + name
            ucx.data = mesh.data.copy()
            ucx.data.name = ucx.name
            ucx.animation_data_clear()
            
            for collection in ucx.users_collection:
                collection.objects.unlink(ucx)
            
            into.objects.link(ucx)


settings = _Settings()

layer = bpy.context.view_layer
active = layer.objects.active
selection = bpy.context.selected_objects

operator = VActGenerateUCX()
operator.do_generate(selection, settings)