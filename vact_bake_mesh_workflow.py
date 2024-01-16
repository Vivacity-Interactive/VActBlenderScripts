import bpy, re

class _Settings:
    def __init__(self):
        self.collections = [
            #("Collection", "Baked", bJoin, bEmpty, "Into", "Name")
            ("_Main", "Train_Station_Bake", True, True, None, "SM_%X%_Bake"),
        ]
        self.use_collections = True
        self.into = "_Bake"
        #self.into = "Decor"
        self.name_regex = r'((CURVE_|E_|SM_|SK_)?([^.]*))(\.\d*)?'
        self.name_group = 3
        self.name = "SM_%X%_Bake"
        #self.name = "SM_%X%"
        self.apply_mirror = True
        self.apply_nodes = False
        self.apply_bevel = True
        self.apply_subdivision = False
        self.apply_array = True
        self.apply_particles = True
        self.apply_curve = True
        self.apply_wireframe = True
        self.convert_curver = True
        self.join = False
        self.temp = "_Curves"
        self.name_join = "SM_Joined_Bake"
        self.levels = 1
        self.uv_unwrap = False
        
        self.join_empties = True


class VActBakeMeshWorkflow:
    def do_execute(self, context, settings):
        into = bpy.data.collections[settings.into]
        temp = bpy.data.collections[settings.temp]
        #depsgraph = bpy.context.evaluated_depsgraph_get()
        collections = []
        
        #global_into = into
        #global_name = settings.name
        
        if not settings.use_collections: settings.collections = [None]
        
        _regex = re.compile(settings.name_regex)
        for entry in  settings.collections:            
            if settings.use_collections:
                bpy.ops.object.select_all(action = 'DESELECT')
                settings.name_join = entry[1]
                settings.join = entry[2]
                settings.join_empties = entry[3]
                #into = bpy.data.collections[entry[4]] if entry[4] else global_into
                #settings.name = entry[5] if entry[5] else global_name
                context = []
                self.traverse_collection(bpy.data.collections[entry[0]], context)
        
            bakes = []
            empties = dict()
            
            for mesh in context:
                b_empty = False
                b_mesh = mesh.type in {'MESH'}
                b_curve = settings.convert_curver and mesh.type in {'CURVE'}
                
                if b_curve:
                    bpy.ops.object.select_all(action = 'DESELECT')
                    mesh.select_set(True)
                    bpy.context.view_layer.objects.active = mesh
                    bpy.ops.object.convert(target='MESH', keep_original=True)
                    mesh.select_set(False)
                    mesh = bpy.context.view_layer.objects.active
                    mesh.name.replace('CURVE_', "SM_")
                    mesh.data.name = mesh.name
                    
                    for collection in mesh.users_collection:
                        collection.objects.unlink(mesh)
                    
                    temp.objects.link(mesh)
                    b_mesh = True
                
                if not b_mesh: continue
            
                _match = _regex.match(mesh.name)
                name = settings.name.replace("%X%",_match.group(settings.name_group))
                bake = mesh.copy()
                bake.name = name
                bake.data = mesh.data.copy()
                bake.data.name = bake.name
                bake.animation_data_clear()
                
                for collection in bake.users_collection:
                    collection.objects.unlink(bake)
                
                into.objects.link(bake)
                
                bpy.context.view_layer.objects.active = bake
                for modifier in bake.modifiers:
                    b_particles = settings.apply_mirror and modifier.type in {'PARTICLE_SYSTEM'}
                    if b_particles:
                        bpy.ops.object.modifier_apply(modifier=modifier.name)
                    
                    b_mirror = settings.apply_mirror and modifier.type in {'MIRROR'}
                    if b_mirror:
                        bpy.ops.object.modifier_apply(modifier=modifier.name)
                        
                    b_array = settings.apply_array and modifier.type in {'ARRAY'}
                    if b_array:
                        bpy.ops.object.modifier_apply(modifier=modifier.name)
                        
                    b_curve_m = settings.apply_curve and modifier.type in {'CURVE'}
                    if b_curve_m:
                        bpy.ops.object.modifier_apply(modifier=modifier.name)
                        
                    b_wireframe = settings.apply_wireframe and modifier.type in {'WIREFRAME'}
                    if b_wireframe:
                        bpy.ops.object.modifier_apply(modifier=modifier.name)
                    
                    b_nodes = settings.apply_nodes and modifier.type in {'NODES'}
                    if b_nodes:
                        group = modifier.node_group
                        apply_group = bpy.data.node_groups[group.name + "_Bake"]
                        # todo create duplicate if not exists and 
                        # include 'GeometryNodeRealizeInstances' node before output
                        modifier.node_group = apply_group
                        #nodes = group.nodes
                        bpy.ops.object.modifier_apply(modifier=modifier.name)
                    
                    b_bevel = settings.apply_bevel and modifier.type in {'BEVEL'}
                    if b_bevel:
                        bpy.ops.object.modifier_apply(modifier=modifier.name)
                    
                    b_subdivision = settings.apply_subdivision  and modifier.type in {'SUBSURF'}
                    if b_subdivision:
                        modifier.levels = settings.levels
                        bpy.ops.object.modifier_apply(modifier=modifier.name)
                
                if settings.uv_unwrap:
                    bpy.ops.object.mode_set(mode='EDIT')
                    bpy.ops.mesh.select_all(action = 'SELECT')
                    bpy.ops.uv.unwrap()
                    bpy.ops.object.mode_set(mode='OBJECT')
                   
                if settings.join_empties:
                    b_empty = mesh.parent and mesh.parent.type in {'EMPTY'}
                    if b_empty:
                        if not mesh.parent.name in empties:
                            _match_empty = _regex.match(mesh.parent.name)
                            name_empty = settings.name.replace("%X%",_match_empty.group(settings.name_group))
                            empties[mesh.parent.name] = (name_empty, [])
                        
                        empties[mesh.parent.name][1].append(bake)
                
                if not b_empty: bakes.append(bake)
            
            if settings.join_empties:
                for empty, pair in empties.items():
                    empty_bake = self.do_join(pair[1], into, pair[0])
                    bakes.append(empty_bake)
            
            if settings.join: self.do_join(bakes, into, settings.name_join)
    
    
    def do_join(self, list, into, name):
        mesh = bpy.data.meshes.new(name)
        target = bpy.data.objects.new(name, mesh)
        into.objects.link(target)
        
        bpy.ops.object.select_all(action = 'DESELECT')
        
        target.select_set(True)
        bpy.context.view_layer.objects.active = target
        for bake in list: bake.select_set(True)

        bpy.ops.object.join()
        return target
    

    def traverse_collection(self, collection, list):
        for child in collection.children: self.traverse_collection(child, list)
        for object in collection.objects: list.append(object)
        return list
    
    
    def traverse_object(self, name):
        return []


settings = _Settings()

layer = bpy.context.view_layer
active = layer.objects.active
selection = bpy.context.selected_objects

operator = VActBakeMeshWorkflow()
operator.do_execute(selection, settings)