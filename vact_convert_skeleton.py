import bpy, json, os

class _Settings:
    def __init__(self):
        self.file = os.path.join(os.path.dirname(bpy.data.filepath), "mixamo2vact.json")
        self.include_vertexgroups = True
        self.option = 0

class VActConvertSkeleton:
    def do_execute(self, context, settings):
        
        with open(settings.file) as file:
            map = json.load(file)
        
        option = settings.option
        
        for item in context:
            b_armature = item.type in {'ARMATURE'}
            b_mesh = settings.include_vertexgroups and item.type in {'MESH'}
            
            if b_armature:
                for bone in item.data.bones:
                    options = map.get(bone.name)
                    b_exists = options and options[option]
                    if b_exists: bone.name = options[option]['name']
                    
            elif b_mesh:
                for group in item.vertex_groups:
                    options = map.get(group.name)
                    b_exists = options and options[option]
                    if b_exists: group.name = options[option]['name']
                


settings = _Settings()

layer = bpy.context.view_layer
active = layer.objects.active
selection = bpy.context.selected_objects

operator = VActConvertSkeleton()
operator.do_execute(selection, settings)