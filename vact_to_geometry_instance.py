import bpy, mathutils

def _resolve_collection(object, default):
    for collection in bpy.data.collections:
        if object.name in collection.objects: return collection
    return default

class _VActInstancesEntry:
    def __init__(self, name, instance = None, into = None):
        data = bpy.data.meshes.new(name)
        self.instance = instance
        self.object = bpy.data.objects.new(name, data)
        self.rotations = None
        self.scales = None
        self.objects = []
        self.into = into

    def evaluate(self, name_rotation= "rotation", name_scale = "scale"):
        data = self.object.data
        data.vertices.add(len(self.objects))
        data.update()
        self.rotations = data.attributes.new(name=name_rotation, type='FLOAT_VECTOR', domain='POINT')
        self.scales = data.attributes.new(name=name_scale, type='FLOAT_VECTOR', domain='POINT')


class _Settings:
    def __init__(self):
        self.into = "_Instances"
        self.b_ensure_instance = True
        self.b_instance_grouped = True
        self.b_into_same_collection = True
        self.b_clear_animation_data = False
        self.b_delete_original = True
        self.b_hide_original = True
        self.refs_into = "_References"
        self.name_gx_single = "GX_Instance"
        self.name_gx_grouped = "GX_Instances"
        self.points_reprefix = ("SM_", "GX_")
        self.name_rotation = "_rotation"
        self.name_scale = "_scale"

class VActToGeometryInstance:
    def as_instances(self, context, into, settings):
        _into = into
        _refs_into = bpy.data.collections[settings.into] if settings.refs_into else into
        _groups = {}
        for object in context:
            _id = id(object.data)
            _entry = _groups.get(_id)
            if not _entry:
                _rule_prefix = settings.points_reprefix
                name = object.data.name.replace(_rule_prefix[0], _rule_prefix[1]) if _rule_prefix else object.data.name
                _instance = object
                if settings.b_into_same_collection: _into = _resolve_collection(_instance, into)
                if settings.b_ensure_instance:
                    _instance = object.copy()
                    _instance.data = object.data
                    _instance.parent = None
                    _instance.matrix_world = mathutils.Matrix.Identity(4)
                    if settings.b_clear_animation_data: _instance.animation_data_clear()
                    _refs_into.objects.link(_instance)
                _entry = _VActInstancesEntry(name, _instance, _into)
                print(object.data.name)
                _groups[_id] = _entry
            _entry.objects.append(object)
        
        for _entry in _groups.values():
            _entry.evaluate(settings.name_rotation, settings.name_scale)
            for i, vertex in enumerate(_entry.object.data.vertices):
                object = _entry.objects[i]
                vertex.co = object.location
                _entry.rotations.data[i].vector = object.rotation_euler
                _entry.scales.data[i].vector = object.scale
                if settings.b_delete_original: bpy.data.objects.remove(object)
                elif settings.b_hide_original: object.hide_render = object.hide_viewport = True
            
            node_group = bpy.data.node_groups.get(settings.name_gx_grouped)
            if not node_group:
                node_group = bpy.data.node_groups.new(settings.name_gx_grouped, 'GeometryNodeTree')
                node_group.interface.new_socket(in_out='OUTPUT', socket_type="NodeSocketGeometry", name="Geometry")
                node_group.interface.new_socket(in_out='INPUT', socket_type="NodeSocketGeometry", name="Geometry")
                node_group.interface.new_socket(in_out='INPUT', socket_type="NodeSocketObject", name="Object")
                
                nodes = node_group.nodes
                links = node_group.links

                group_in = nodes.new(type='NodeGroupInput')
                group_out = nodes.new(type='NodeGroupOutput')

                gnx_inst_on = nodes.new(type="GeometryNodeInstanceOnPoints")

                gnx_get_rotation = nodes.new(type="GeometryNodeInputNamedAttribute")
                gnx_get_rotation.data_type = 'FLOAT_VECTOR'
                gnx_get_rotation.inputs[0].default_value = settings.name_rotation
                
                gnx_get_scale = nodes.new(type="GeometryNodeInputNamedAttribute")
                gnx_get_scale.data_type = 'FLOAT_VECTOR'
                gnx_get_scale.inputs[0].default_value = settings.name_scale

                gnx_info_object = nodes.new(type="GeometryNodeObjectInfo")
                gnx_info_object.transform_space = 'ORIGINAL'
                gnx_info_object.inputs[1].default_value = True
                
                links.new(group_in.outputs[0], gnx_inst_on.inputs[0])
                links.new(group_in.outputs[1], gnx_info_object.inputs[0])
                links.new(gnx_info_object.outputs[4], gnx_inst_on.inputs[2])
                links.new(gnx_get_rotation.outputs[0], gnx_inst_on.inputs[5])
                links.new(gnx_get_scale.outputs[0], gnx_inst_on.inputs[6])
                links.new(gnx_inst_on.outputs[0], group_out.inputs[0])
                
                group_in.location = (-200, 0)
                group_out.location = (200, 0)
            
            modifier = _entry.object.modifiers.new(settings.name_gx_grouped, "NODES")
            modifier.node_group = node_group
            modifier["Socket_2"] = _entry.instance

            _into.objects.link(_entry.object)

    def to_instance(self, context, settings):
        node_group = bpy.data.node_groups.get(settings.name_gx_single)
        if not node_group:
            node_group = bpy.data.node_groups.new(settings.name_gx_single, 'GeometryNodeTree')
            node_group.interface.new_socket(in_out='OUTPUT', socket_type="NodeSocketGeometry", name="Geometry")
            node_group.interface.new_socket(in_out='INPUT', socket_type="NodeSocketGeometry", name="Geometry")

            nodes = node_group.nodes
            links = node_group.links

            group_in = nodes.new(type='NodeGroupInput')
            group_out = nodes.new(type='NodeGroupOutput')

            gnx_to_inst = nodes.new(type="GeometryNodeGeometryToInstance")
            links.new(group_in.outputs[0], gnx_to_inst.inputs[0])
            links.new(gnx_to_inst.outputs[0], group_out.inputs[0])
                
            group_in.location = (-200, 0)
            group_out.location = (200, 0)
        
        modifier = context.modifiers.new(settings.name_gx_single, "NODES")
        modifier.node_group = node_group
        
    def do_execute(self, context, settings):
        into = bpy.data.collections[settings.into] if settings.into else bpy.context.scene.collection

        if settings.b_instance_grouped:
            self.as_instances(context, into, settings)
        else:
            for item in context: self.to_instance(item, settings)

settings = _Settings()

layer = bpy.context.view_layer
active = layer.objects.active
selection = bpy.context.selected_objects

operator = VActToGeometryInstance()
operator.do_execute(selection, settings)