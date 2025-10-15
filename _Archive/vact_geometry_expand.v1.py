import bpy, mathutils, math

def _resolve_collection(object, default):
    for collection in bpy.data.collections:
        if object.name in collection.objects: return collection
    return default

class _DummyObject:
    def __init__(self, matrix_world, data = None, parent = None):
        self.data = data
        self.matrix_world = matrix_world
        self.parent = parent
        

class _Settings:
    def __init__(self):
        self.target = ('SM_',)
        self.b_target = False
        self.b_remove = False
        self.b_expand_filter = True
        self.node_groups_remove = {'GN_Single'}
        self.node_groups_expand = {'GN_Array', 'GN_Mirror', 'GN_Path'}
        self.b_expand = True
        self.b_delete_original = False #True
        self.expand_into = "_Colony_87T_Far_02" #"_Colony_87T_Appartment"#"_Expanded" #"_Colony_87T_Half_Tunnel"
        self.max_depth = -1
        self.b_clear_modifiers = True
        self.b_clear_animation_data = False
        self.b_into_same_collection = False #True
        #self.b_select_expanded = True

class VActGeometryExpand:
    def do_instantiate(self, context, matrix_world, parent, into, settings):
        _object = context.copy()
        _object.data = context.data
        _object.parent = parent
        _object.matrix_world = matrix_world
       
        if settings.b_clear_animation_data:_object.animation_data_clear()
        if settings.b_clear_modifiers:
            b_filter = settings.b_expand_filter and len(settings.node_groups_expand) > 0
            for modifier in _object.modifiers[:]:
                b_remove = (modifier.type in {'NODES'} and modifier.node_group 
                            and ((not b_filter) or modifier.node_group.name in settings.node_groups_expand))
                if b_remove: _object.modifiers.remove(modifier)
        
        into.objects.link(_object)
        
    def do_collection(self, context, matrix_world, depsgraph, parent, depth, into, settings):
        #print(('-geomi', 'collection', context.name))
        for _ref_object in context.all_objects:
            _object = bpy.data.objects.get(_ref_object.name) if _ref_object else None
            if _object:
                _matrix_world = matrix_world @ _object.matrix_world
                print(("-geomi", 'collection', "child", _object.name, _object.data.name, context.name))
                _parent = self.do_instantiate(_object, _matrix_world, parent, into, settings)
                if not _parent: _parent = _DummyObject(_matrix_world)
                # TODO check if instance position is tranfered properly
                self.do_expand(_object, _parent, depsgraph, depth - 1, into, settings)

    def do_expand(self, context, parent, depsgraph, max_depth, into, settings):
        if max_depth == 0: return

        eval_obj = depsgraph.id_eval_get(context)
        b_evaluated = eval_obj and eval_obj.is_evaluated
        eval_geom = eval_obj.evaluated_geometry() if b_evaluated else None
        if not eval_geom: return

        cloud = eval_geom.instances_pointcloud()
        references = eval_geom.instance_references()
        b_cloud = cloud and references
        if not b_cloud: return

        _indicie = cloud.attributes[".reference_index"]
        _transforms = cloud.attributes["instance_transform"]
        _object = None
        _base = parent.matrix_world if parent else mathutils.Matrix.Identity(4)
        for _index in range(len(cloud.points)):
            index = _indicie.data[_index].value
            _matrix = _matrix_world = (_base @ _transforms.data[_index].value)
            reference = references[index]
            if isinstance(reference, bpy.types.GeometrySet):
                _collection = bpy.data.collections.get(reference.name)
                if _collection: self.do_collection(_collection, _matrix_world, depsgraph, None, max_depth, into, settings)
                else:
                    _object = bpy.data.objects.get(reference.name)
                    if _object:
                        #print(("-geomi", "geometryset", "object", reference.name, _object.name, _object.data.name))
                        _parent = self.do_instantiate(_object, _matrix_world, None, into, settings)
                        # TODO check if instance position is tranfered properly
                        self.do_expand(_object, _parent, depsgraph, max_depth - 1, into, settings)
                    else:
                        #print(("-geomi", "geonoset", "object", reference.name))
                        # TODO fix test if context.data equals _mesh if not than fine otherwise skip
                        _mesh = bpy.data.meshes.get(reference.mesh.name) if reference.mesh else None
                        
                        # TODO find out what to do when mesh is generated needs
                        # b_generated = not _mesh and reference.mesh
                        # if b_generated:
                        #     _mesh = reference.mesh.to_mesh().copy()
                        #     _mesh.name = reference.name or f"{context.name}_{_index}"
                        
                        if _mesh:
                            _object = bpy.data.objects.new(_mesh.name, _mesh)
                            #print(("-geomi", "geometryset", "mesh", reference.name, _object.name, _object.data.name))
                            _parent = self.do_instantiate(_object, _matrix_world, None, into, settings)
                            # TODO check if instance position is tranfered properly
                            self.do_expand(_object, _parent, depsgraph, max_depth - 1, into, settings)
                            bpy.data.objects.remove(_object)
            elif isinstance(reference, bpy.types.Object):
                _object = bpy.data.objects.get(reference.name)
                if _object:
                    #print(('-geomi', 'object', reference.name, _object.name, _object.data.name))
                    _parent = self.do_instantiate(_object, _matrix_world, None, into, settings)
                    # TODO check if instance position is tranfered properly
                    self.do_expand(_object, _parent, depsgraph, max_depth - 1, into, settings)
            elif isinstance(reference, bpy.types.Collection):
                _collection = bpy.data.collections.get(reference.name)
                if _collection:
                    print(('-geomi', 'collection', _collection.name))
                    self.do_collection(_collection, _matrix_world, depsgraph, None, max_depth, into, settings)
            else: print(('-geomi', 'miss', reference.name))

    def do_execute(self, context, settings):
        _into = into = bpy.data.collections[settings.expand_into] if settings.expand_into else bpy.context.scene.collection
        
        b_remove = settings.b_remove and len(settings.node_groups_remove) > 0
        b_filter = settings.b_expand_filter and len(settings.node_groups_expand) > 0
        b_target = settings.b_target and len(settings.target) > 0
        
        depsgraph = bpy.context.evaluated_depsgraph_get()
        for item in context:
            if settings.b_into_same_collection: _into = _resolve_collection(item, into)
            b_expand = len(item.modifiers) > 0
            b_check = (b_filter or b_remove) and b_expand and (b_target and item.name.startswith(settings.target))
            if b_check:
                b_expand = b_expand and not b_filter
                for modifier in item.modifiers[:]:
                    if modifier.type in {'NODES'} and modifier.node_group:
                        b_expand = b_expand or (not b_filter) or (modifier.node_group.name in settings.node_groups_expand)
                        if b_remove and modifier.node_group.name in settings.node_groups_remove: item.modifiers.remove(modifier)
            
            if b_expand:
                self.do_expand(item, item, depsgraph, -1, _into, settings)
                if settings.b_delete_original: bpy.data.objects.remove(item)
                


settings = _Settings()

layer = bpy.context.view_layer
active = layer.objects.active
selection = bpy.context.selected_objects

operator = VActGeometryExpand()
operator.do_execute(selection, settings)