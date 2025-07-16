import bpy, mathutils

def _resolve_collection(object, default):
    for collection in bpy.data.collections:
        if object.name in collection.objects: return collection
    return default

class _VActLODsEntry:
    def __init__(self, name, instance = None):
        data = bpy.data.meshes.new(name)
        data.vertices.add(1)
        data.update()
        self.object = bpy.data.objects.new(name, data)
        self.objects = []

class _Settings:
    def __init__(self):
        self.into = "_LODs"
        self.b_into_same_collection = False
        self.name_lodx = "GNX_LODx%N%"
        self.points_reprefix = ("SM_", "GX_")
        self.name_camera = "Camera"
        self.norm_distance = 150
        self.b_use_culling = False
        self.culling_weight = 0.6
        self.camera_forward =  mathutils.Vector((0.0, 0.0, -1.0))
        self.factor_power = 2
        self.b_force = False
        self.b_use_scale_inverse = True

class VActToGeometryLOD:
    def as_lod(self, context, camera, into, settings):
        _into = into
        _groups = {}
        for object in context:
            b_lod = (not object.type in {'EMPTY'}) and (object.parent and (object.parent.type in {'EMPTY'}))
            if not b_lod: continue

            _id = id(object.parent)
            _entry = _groups.get(_id)
            if not _entry:
                _rule_prefix = settings.points_reprefix
                name = object.data.name.replace(_rule_prefix[0], _rule_prefix[1]) if _rule_prefix else object.data.name
                _instance = object.parent
                if settings.b_into_same_collection: _into = _resolve_collection(_instance, into)
                _entry = _VActLODsEntry(name, _instance)
                print(object.data.name)
                _groups[_id] = _entry
            _entry.objects.append(object)
        
        for _entry in _groups.values():
            _offset = 7
            _len = len(_entry.objects)
            _name = settings.name_lodx.replace("%N%", str(int(_len)))
            
            node_group = bpy.data.node_groups.get(_name)
            if not node_group:
                node_group = bpy.data.node_groups.new(_name, 'GeometryNodeTree')
                node_group.interface.new_socket(in_out='OUTPUT', socket_type="NodeSocketGeometry", name="Geometry")
                gix0 = node_group.interface.new_socket(in_out='INPUT', socket_type="NodeSocketGeometry", name="Geometry")
                
                gix1 = node_group.interface.new_socket(in_out='INPUT', socket_type="NodeSocketObject", name="Camera")
                gix2 = node_group.interface.new_socket(in_out='INPUT', socket_type="NodeSocketFloat", name="Norm Distance")
                gix2.subtype="DISTANCE"
                gix2.min_value = 0
                gix3 = node_group.interface.new_socket(in_out='INPUT', socket_type="NodeSocketBool", name="Use Culling")
                gix4 = node_group.interface.new_socket(in_out='INPUT', socket_type="NodeSocketFloat", name="Culling Weight")
                gix4.subtype="FACTOR"
                gix4.max_value = 1
                gix4.min_value = 0
                gix5 = node_group.interface.new_socket(in_out='INPUT', socket_type="NodeSocketVector", name="Camera Forward")
                gix3 = node_group.interface.new_socket(in_out='INPUT', socket_type="NodeSocketBool", name="Use Scale Inverse")

                for i, lod in enumerate(_entry.objects):
                    node_group.interface.new_socket(in_out='INPUT', socket_type="NodeSocketObject", name=f"LOD{i}")
                
                for i, lod in enumerate(_entry.objects):
                    gix_lod = node_group.interface.new_socket(in_out='INPUT', socket_type="NodeSocketFloat", name=f"Factor LOD{i}")
                    gix_lod.subtype="FACTOR"
                    gix_lod.max_value = 1
                    gix_lod.min_value = 0

                nodes = node_group.nodes
                links = node_group.links

                group_in = nodes.new(type='NodeGroupInput')
                group_out = nodes.new(type='NodeGroupOutput')

                gnx_self = nodes.new(type="GeometryNodeSelfObject")
                
                gnx_info_object_self = nodes.new(type="GeometryNodeObjectInfo")
                gnx_info_object_self.inputs[1].default_value = True

                gn_switch_scale = nodes.new(type="GeometryNodeSwitch")
                gn_switch_scale.input_type = 'VECTOR'

                shx_vector_math_mul = nodes.new(type="ShaderNodeVectorMath")
                shx_vector_math_mul.operation = 'MULTIPLY'

                gnx_inst_on = nodes.new(type="GeometryNodeInstanceOnPoints")
                gnx_inst_on.inputs[3].default_value = True

                gnx_info_object = nodes.new(type="GeometryNodeObjectInfo")
                gnx_info_object.transform_space = 'RELATIVE'
                gnx_info_object.inputs[1].default_value = True

                gnx_join = nodes.new(type="GeometryNodeJoinGeometry")
                gnx_join_smp = nodes.new(type="GeometryNodeJoinGeometry")

                gnx_sample_nearest = nodes.new(type="GeometryNodeSampleNearest")

                shx_vector_math_sub = nodes.new(type="ShaderNodeVectorMath")
                shx_vector_math_sub.operation = 'SUBTRACT'

                shx_vector_math_nor = nodes.new(type="ShaderNodeVectorMath")
                shx_vector_math_nor.operation = 'NORMALIZE'

                shx_combine_xyz = nodes.new(type="ShaderNodeCombineXYZ")
                
                shx_math_add = nodes.new(type="ShaderNodeMath")
                shx_math_add.operation = 'ADD'
                shx_math_add.inputs[1].default_value = 1.0

                shx_math_div = nodes.new(type="ShaderNodeMath")
                shx_math_div.operation = 'DIVIDE'

                shx_math_div_2 = nodes.new(type="ShaderNodeMath")
                shx_math_div_2.operation = 'DIVIDE'
                shx_math_div_2.inputs[1].default_value = 2.0

                shx_vector_math_len = nodes.new(type="ShaderNodeVectorMath")
                shx_vector_math_len.operation = 'LENGTH'

                shx_vector_math_dot = nodes.new(type="ShaderNodeVectorMath")
                shx_vector_math_dot.operation = 'DOT_PRODUCT'

                fx_compare = nodes.new(type="FunctionNodeCompare")
                fx_compare.operation = 'GREATER_EQUAL'
                
                fx_rotate_vector = nodes.new(type="FunctionNodeRotateVector")

                gn_switch = nodes.new(type="GeometryNodeSwitch")
                gn_switch.input_type = 'BOOLEAN'
                gn_switch.inputs[1].default_value = True

                gn_position = nodes.new(type="GeometryNodeInputPosition")

                for i, lod in reversed(list(enumerate(_entry.objects))): # Todo find better fix
                    gnx_info_object_lod = nodes.new(type="GeometryNodeObjectInfo")
                    gnx_info_object_lod.transform_space = 'ORIGINAL'
                    gnx_info_object_lod.inputs[1].default_value = True
                    links.new(group_in.outputs[_offset + i], gnx_info_object_lod.inputs[0])
                    links.new(gnx_info_object_lod.outputs[4], gnx_join.inputs[0])
                    
                    shx_combine_xyz_lod = nodes.new(type="ShaderNodeCombineXYZ")
                    gnx_points_lod = nodes.new(type="GeometryNodePoints")

                    links.new(group_in.outputs[_offset + _len + i], shx_combine_xyz_lod.inputs[0])
                    links.new(shx_combine_xyz_lod.outputs[0], gnx_points_lod.inputs[1])
                    links.new(gnx_points_lod.outputs[0], gnx_join_smp.inputs[0])
                
                links.new(gnx_self.outputs[0], gnx_info_object_self.inputs[0])
                links.new(gnx_info_object_self.outputs[3], shx_vector_math_mul.inputs[0])
                links.new(gnx_info_object.outputs[1], shx_vector_math_mul.inputs[1])
                links.new(shx_vector_math_mul.outputs[0], gn_switch_scale.inputs[2])
                links.new(gnx_info_object.outputs[1], gn_switch_scale.inputs[1])
                links.new(group_in.outputs[6], gn_switch_scale.inputs[0])
                
                links.new(gnx_join_smp.outputs[0], gnx_sample_nearest.inputs[0])
                links.new(gnx_sample_nearest.outputs[0], gnx_inst_on.inputs[4])

                links.new(gnx_join.outputs[0], gnx_inst_on.inputs[2])
                links.new(group_in.outputs[0], gnx_inst_on.inputs[0])
                links.new(gnx_inst_on.outputs[0], group_out.inputs[0])
                
                links.new(group_in.outputs[1], gnx_info_object.inputs[0])

                links.new(gn_position.outputs[0], shx_vector_math_sub.inputs[0])
                links.new(gn_switch_scale.outputs[0], shx_vector_math_sub.inputs[1])

                links.new(shx_vector_math_sub.outputs[0], shx_vector_math_len.inputs[0])
                links.new(shx_vector_math_sub.outputs[0], shx_vector_math_nor.inputs[0])

                links.new(group_in.outputs[2], shx_math_div.inputs[1])
                links.new(shx_vector_math_len.outputs[1], shx_math_div.inputs[0])
                links.new(shx_vector_math_dot.outputs[1], shx_math_add.inputs[0])
                
                links.new(shx_math_div.outputs[0], shx_combine_xyz.inputs[0])

                links.new(shx_combine_xyz.outputs[0], gnx_sample_nearest.inputs[1])
            
                links.new(group_in.outputs[5], fx_rotate_vector.inputs[0])
                links.new(gnx_info_object.outputs[2], fx_rotate_vector.inputs[1])

                links.new(shx_vector_math_nor.outputs[0], shx_vector_math_dot.inputs[0])
                links.new(fx_rotate_vector.outputs[0], shx_vector_math_dot.inputs[1])
                
                links.new(shx_math_add.outputs[0], shx_math_div_2.inputs[0])

                links.new(shx_math_div_2.outputs[0], fx_compare.inputs[0])
                links.new(group_in.outputs[4], fx_compare.inputs[1])
                links.new(fx_compare.outputs[0], gn_switch.inputs[2])
                links.new(group_in.outputs[3], gn_switch.inputs[0])

                links.new(gn_switch.outputs[0], gnx_inst_on.inputs[1])
                
                group_in.location = (-200, 0)
                group_out.location = (200, 0)

            modifier = _entry.object.modifiers.new(_name, "NODES")
            modifier.node_group = node_group
            modifier["Socket_2"] = camera
            modifier["Socket_3"] = settings.norm_distance
            modifier["Socket_4"] = settings.b_use_culling
            modifier["Socket_5"] = settings.culling_weight
            modifier["Socket_6"] = settings.camera_forward
            modifier["Socket_7"] = settings.b_use_scale_inverse

            for i, lod in enumerate(_entry.objects):
                modifier[f"Socket_{i + _offset + 1}"] = lod
                modifier[f"Socket_{i + _offset + _len + 1}"] = pow(i/_len, settings.factor_power)

            _into.objects.link(_entry.object)
            modifier.node_group.update_tag()
        
    def do_execute(self, context, settings):
        into = bpy.data.collections[settings.into] if settings.into else bpy.context.scene.collection
        camera = bpy.data.objects[settings.name_camera]
        self.as_lod(context, camera, into, settings)

settings = _Settings()

layer = bpy.context.view_layer
active = layer.objects.active
selection = bpy.context.selected_objects

operator = VActToGeometryLOD()
operator.do_execute(selection, settings)