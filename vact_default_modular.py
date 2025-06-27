import bpy, re

class _Settings:
    def __init__(self):
        self.ungroupd_name = None
        self.name_regex = r'(MA|E|SM)_([a-zA-Z0-9]+_[a-zA-Z0-9]+)_((([a-zA-Z0-9]+)(_[a-zA-Z0-9]+)?)_(\d+))(\.\d+)?'
        self.name_replace = r'MA_\2_\7'
        self.tree_name_replace = r'GN_\2'
        self.input_name_replace = r'\4'
        self.input_name_clean = r'[_\.-]+'
        self.group_by = r'\2\7'
        self.use_group_by_regex = True
        self.use_group_by_empty = False
        self.use_transform = True
        self.into = "Modular"
        self.use_collections = False
        self.use_existing_nodes = True
        self.use_placement = True
        self.use_promote_placement = False
        self.use_dimensions = False
        self.use_range = True
        self.use_bounds = False
        self.do_order_by_name = True
        self.default_parms = [
            ("Scatter", None, None, None, "NodeSocketObject", 'INPUT', None)
        ]

class VActDefaultModular:
    class _Cursor:
        def __init__(self):
            # golbal
            self.trees = None
            self.regex = None
            self.clean = None
            # local
            self.reset_locals()
        
        def reset_locals(self):
            self.inputs = {}
            self.group = None
            self.index = -1
            self.index_location = -1
            self.index_rotation = -1
            self.index_scale = -1
        
        
    def do_execute(self, context, settings):
        _cursor = VActDefaultModular._Cursor()
        _cursor.trees = {}
        _grouped = {}
    
        into = bpy.data.collections[settings.into]
        _cursor.regex = re.compile(settings.name_regex)
        _cursor.clean = re.compile(settings.input_name_clean)
        
        if settings.use_group_by_empty:
            for item in context:
                b_parent = item.parent and item.parent.type in {'EMPTY'}
                if b_parent:
                    if item.parent.name not in _grouped:
                        #name = _cursor.regex.sub(settings.name_replace, item.parent.name)
                        _grouped[item.parent.name] = (item.parent.name, [])
                    _grouped[item.parent.name][1].append(item) 
        
        if settings.use_group_by_regex:
            for item in context:
                _key = _cursor.regex.sub(settings.group_by, item.name)
                
                if _key not in _grouped:
                    #name = _cursor.regex.sub(settings.name_replace, item.name)
                    _grouped[_key] = (item.name, [])
                _grouped[_key][1].append(item)
                
        b_grouped = settings.use_group_by_empty or settings.use_group_by_regex
        
        if not b_grouped: _grouped[settings.ungroupd_name if settings.ungroupd_name else "SM_Ungrouped"]
        
        for name, items in _grouped.values():
            _name = _cursor.regex.sub(settings.name_replace, name)
            mesh = bpy.data.meshes.new(_name)
            item = bpy.data.objects.new(mesh.name, mesh)
            into.objects.link(item)
        
            _name_nodes = _cursor.regex.sub(settings.tree_name_replace, name)
            modifier = item.modifiers.new(_name_nodes, "NODES")
        
            _tree = _cursor.trees.get(_name_nodes) 
            
            if not _tree: self.create_modular_base(_name_nodes, items, _cursor, settings)
            
            _tree = _cursor.trees[_name_nodes]
            group = _tree[0]
            inputs = _tree[1]
            
            modifier.node_group = group
            
            for item in items:
                _name = _cursor.clean.sub(r' ', _cursor.regex.sub(settings.input_name_replace, item.name))
                modifier[inputs[_name]] = item
                # TODO b_promoted not used
                b_promoted = settings.use_placement and settings.use_promote_placement
                if settings.use_promote_placement:
                    modifier[inputs[f"Offset {_name}"]] = item.location
                    modifier[inputs[f"Rotation {_name}"]] = item.rotation_euler
                    #modifier[inputs[f"Scale {_name}"]] = item.scale
        
        #b_reorder = settings.do_order_by_name and _cursor.trees 
        #if b_reorder: self.reorder_sockets(_cursor, settings)
    
    #def reorder_sockets(self, cursor, settings):
    #    for name, tree in cursor.trees.items():
    #        group = tree[0]
    #        inputs = tree[1]
    #        pairs = inputs.items()
    #        indices = sorted(range(len(pairs)), key=lambda i: pairs[i])
    #        for new in range(len(indices)):
    #            old = indices[new]
    #            group.inputs.move(old, new)
    #            #temp = indices[old]
    #            #indices[old] = new
    #            #indices[temp] = old
            
    
    def create_modular_base(self, name, items, cursor, settings):
        # reset cursor local part
        cursor.reset_locals()
        
        b_exists = settings.use_existing_nodes and self.find_modular_base(name, cursor, settings)
        if b_exists: return
        
        gnx_transform = None
        shx_range = None
        shx_combine = None
        gnx_bounds = None
        shx_range_combine = None
        shx_bounds_subtract = None
        shx_offset_add = None
        
        cursor.group = bpy.data.node_groups.new(name, 'GeometryNodeTree')
        cursor.group.interface.new_socket(in_out='OUTPUT', socket_type="NodeSocketGeometry", name="Geometry")
        
        nodes = cursor.group.nodes
        links = cursor.group.links
        
        group_in = nodes.new(type='NodeGroupInput')
        group_in.location = (-200, 0)
        group_out = nodes.new(type='NodeGroupOutput')
        group_out.location = (200, 0)
        
        gnx_join = nodes.new(type="GeometryNodeJoinGeometry")
        links.new(gnx_join.outputs[0], group_out.inputs[0])   
        
        for item in items:
            _name = cursor.clean.sub(r' ', cursor.regex.sub(settings.input_name_replace, item.name))
            self.promote_parm((_name, None, None, None, "NodeSocketObject", 'INPUT', None), cursor, settings) 
            gnx_info = nodes.new(type="GeometryNodeObjectInfo")
            links.new(group_in.outputs[cursor.index], gnx_info.inputs[0])
            lx_out = gnx_info.outputs[3]
            
            if settings.use_promote_placement:
                    self.promote_parm((f"Offset {_name}", None, None, None, "NodeSocketVector", 'INPUT', "TRANSLATION"), cursor, settings)
                    cursor.index_location = cursor.index
                    self.promote_parm((f"Rotation {_name}", None, None, None, "NodeSocketVector", 'INPUT', "TRANSLATION"), cursor, settings)
                    cursor.index_rotation = cursor.index
                    #self.promote_parm((f"Scale {_name}", None, None, None, "NodeSocketVector", 'INPUT', "TRANSLATION"), cursor, settings)
                    #cursor.index_scale = cursor.index
             
            if settings.use_placement:
                gnx_transform = nodes.new(type="GeometryNodeTransform")
                
                shx_offset_add = nodes.new(type="ShaderNodeVectorMath")
                shx_offset_add.operation = "ADD"
                links.new(shx_offset_add.outputs[0], gnx_transform.inputs[1])
                
                shx_rotation_add = nodes.new(type="ShaderNodeVectorMath")
                shx_rotation_add.operation = "ADD"
                links.new(shx_rotation_add.outputs[0], gnx_transform.inputs[2])
                
                #shx_scale_multiply = nodes.new(type="ShaderNodeVectorMath")
                #shx_scale_multiply.operation = "MULTIPLY"
                #links.new(shx_scale_multiply.outputs[0], gnx_transform.inputs[3])
                
                links.new(lx_out, gnx_transform.inputs[0])
                lx_out = gnx_transform.outputs[0]
                if settings.use_promote_placement:
                    links.new(group_in.outputs[cursor.index_location], shx_offset_add.inputs[0])
                    links.new(group_in.outputs[cursor.index_rotation], shx_rotation_add.inputs[0])
                    #links.new(group_in.outputs[cursor.index_scale], shx_scale_multiply.inputs[0])
                else:
                    shx_offset_add.inputs[0].default_value = item.location
                    shx_rotation_add.inputs[0].default_value = item.rotation_euler 
                    #shx_scale_multiply.inputs[0].default_value = item.scale
                
            if settings.use_range:
                shx_range = nodes.new(type="ShaderNodeMapRange")
                shx_range_combine = nodes.new(type="ShaderNodeCombineXYZ")
                self.promote_parm((f"Factor {_name}", 0, 1, 0, "NodeSocketFloat", 'INPUT', "FACTOR"), cursor, settings)
                links.new(group_in.outputs[cursor.index], shx_range.inputs[0])
                links.new(shx_range.outputs[0], shx_range_combine.inputs[2])
                if shx_offset_add: links.new(shx_range_combine.outputs[0], shx_offset_add.inputs[1])
                
            if settings.use_dimensions:
                shx_combine = nodes.new(type="ShaderNodeCombineXYZ")
                shx_combine.label = f"Bounds {_name}"
                shx_combine.inputs[0].default_value = item.dimensions.x
                shx_combine.inputs[1].default_value = item.dimensions.y
                shx_combine.inputs[2].default_value = item.dimensions.z
            
            if settings.use_bounds:
                gnx_bounds = nodes.new(type="GeometryNodeBoundBox")
                shx_bounds_subtract = nodes.new(type="ShaderNodeVectorMath")
                shx_bounds_subtract.operation = "SUBTRACT" 
                links.new(gnx_info.outputs[3], gnx_bounds.inputs[0])
                links.new(gnx_bounds.outputs[1], shx_bounds_subtract.inputs[1])
                links.new(gnx_bounds.outputs[2], shx_bounds_subtract.inputs[0])
                
            links.new(lx_out, gnx_join.inputs[0])
        
        for entry in settings.default_parms:
            self.promote_parm(entry, cursor, settings)
         
        cursor.trees[name] = (cursor.group, cursor.inputs)
    
    def promote_parm(self, entry, cursor, settings):
        gix_parm = cursor.group.interface.new_socket(in_out=entry[5], socket_type=entry[4], name=entry[0])
        if entry[2] is not None: gix_parm.max_value = entry[2]
        if entry[1] is not None: gix_parm.min_value = entry[1]
        if entry[3] is not None: gix_parm.default_value = entry[3]
        if entry[6] is not None: gix_parm.subtype = entry[6]
        cursor.index += 1
        cursor.inputs[entry[0]] = f"Socket_{cursor.index + 1}"
    
    def find_modular_base(self, name, cursor, settings):
        b_exists = False
        for group in bpy.data.node_groups:
            b_exists = group.name == name and group.type in {'GeometryNodeTree'}
            if b_exists:
                cursor.group = group
                cursor.inputs = { socket.identifier : socket for socket in cursor.group.interface.items_tree if socket.in_out in {'INPUT'} }
                cursor.index = len(cursor.inputs) - 1
                cursor.trees[name] = (cursor.group, cursor.inputs)
                break
        return b_exists
        
        
            
settings = _Settings()

layer = bpy.context.view_layer
active = layer.objects.active
selection = bpy.context.selected_objects

operator = VActDefaultModular()
operator.do_execute(selection, settings)