import bpy, bmesh, mathutils 

class _Settings:
    def __init__(self):
        self.attribute_name = "uv_seam"
        self.b_keep_existing = True

class VActApplyGeometryUV:
    def do_execute(self, context, settings):
        depsgraph = bpy.context.evaluated_depsgraph_get()
        for item in context:
            if not item.type in { 'MESH' }: continue
            item_eval = item.evaluated_get(depsgraph)
            mesh_eval = item_eval.to_mesh()
            mesh = item.data
            bpy.ops.object.mode_set(mode='OBJECT')
            if settings.attribute_name in mesh_eval.attributes:
                attribute = mesh_eval.attributes[settings.attribute_name].data
                for index, edge in enumerate(mesh.edges):
                    edge.use_seam = attribute[index].value or (settings.b_keep_existing and edge.use_seam)
            
            item_eval.to_mesh_clear()

settings = _Settings()

layer = bpy.context.view_layer
active = layer.objects.active
selection = bpy.context.selected_objects

operator = VActApplyGeometryUV()
operator.do_execute(selection, settings)