import bpy

class _Settings:
    def __init__(self):
        self.into = "LOD"
        self.lod_levels = 3
        self.do_rename = True
        self.do_decimate = False


class VActGenerateLOD:
    def do_generate(self, context, settings):
        into = bpy.data.collections[settings.into]
        
        for mesh in context:
            b_mesh = mesh.type in {'MESH'}
            if not b_mesh: continue
            if settings.do_rename:
                mesh.name = mesh.name + "_LOD0"
                mesh.data.name = mesh.name
            name = mesh.name.replace("_LOD0","_LOD")
            for level in range(1, settings.lod_levels):
                lod = mesh.copy()
                lod.name = name + str(level)
                lod.data = mesh.data.copy()
                lod.data.name = lod.name
                lod.animation_data_clear()
                
                for collection in lod.users_collection:
                    collection.objects.unlink(lod)
                
                into.objects.link(lod)


settings = _Settings()

layer = bpy.context.view_layer
active = layer.objects.active
selection = bpy.context.selected_objects

operator = VActGenerateLOD()
operator.do_generate(selection, settings)