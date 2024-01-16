import bpy

class _Settings:
    def __init__(self):
        self.into = None
        self.target_lod = "_LOD0"
        self.fbx_type = "LodGroup"


class VActGroupLOD:
    def do_generate(self, context, settings):
        into = bpy.data.collections[settings.into] if settings.into else None
        
        for mesh in context:
            b_mesh = mesh.type in {'MESH'}
            if not b_mesh: continue
            name = mesh.name.replace(settings.target_lod,"")
            
            bpy.ops.object.select_all(action='DESELECT')
            bpy.ops.object.select_pattern(pattern=name + "_LOD[0-9]*", extend=False)
            lods = bpy.context.selected_objects
            
            group = bpy.data.objects.new(name, None)
            group['fbx_type'] = settings.fbx_type
            
            for lod in lods:
                lod.parent = group
            
            if into: into.objects.link(group)
            else:
                for collection in mesh.users_collection: collection.objects.link(group)
            


settings = _Settings()

layer = bpy.context.view_layer
active = layer.objects.active
selection = bpy.context.selected_objects

operator = VActGroupLOD()
operator.do_generate(selection, settings)