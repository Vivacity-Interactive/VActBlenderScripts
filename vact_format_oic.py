import bpy, json, mathutils, math, itertools, os, struct, sys, re

from bpy_extras import (
    io_utils
)

from collections import (
    deque
)


class _VAct_OICCursor:
     def __init__(self):
        self.links = []
        self.objects = {}
        self.instance_meta = []
        self.axis = mathutils.Matrix.Identity(4)

class VActList(list):
    def __next__(self):
        size = len(self)
        for index in range(size):
            yield self[index]
        
    def __previous__(self):
        size = len(self)
        for index in range(size):
            yield self[size - index - 1]
    
    def __iter__(self):
        return self.__next__()
    
    def reverse(self):
        return self.__previous__()


class VActQueue(deque):
    def __next__(self):
        while self:
            yield self.popleft()
        
    def __previous__(self):
        while self:
            yield self.pop()
    
    def __iter__(self):
        return self.__next__()
    
    def reverse(self):
        return self.__previous__()
    

class VActStack(deque):        
    def __next__(self):
        while self:
            yield self.pop()
        
    def __previous__(self):
        while self:
            yield self.popleft()
    
    def __iter__(self):
        return self.__next__()
    
    def reverse(self):
        return self.__previous__()


class VActOIC:
    class Property:
        def __init__(self):
            self._type = "_"
            self.name = "_Unknown"
            self.value = None


    class Instance:
        def __init__(self):
            self.id = -1
            self.object = -1
            self.transform = None
    
    
    class Link:
        def __init__(self):
            self.is_relative = True
            self.type = "_Unknown"
            self.file = ""
    
    
    class Object:
        def __init__(self):
            self.id = -1
            self.name = "_Unknown"
            self.link = None
            self.meta = []        
    
    
    class Entry:
        def __init__(self):
            self.id = -1
            self.meta = []
    
    
    def __init__(self, name="_Nameless" ):
        self._type = "OIC"
        self._version = 1
        self._format = "_Unknown"
        self.name = name
        self.topology = "_Unknown"
        self.axis = "_Unknown"
        self.transform = []
        self.objects = []
        self.instances = []
    
    def add_instance(self, item):
        item.id = len(self.instances)
        self.instances.append(item)
        return item.id
    
    def add_object(self, item):
        item.id = len(self.objects)
        self.objects.append(item)
        return item.id
    
    def optimize(self):
        pass


class _VAct_OICEncoder(json.JSONEncoder):
    def default(self, o):
        return o.__dict__
    
    def compact(self, o):
        Q = VActStack([o])
        return VActList((q for q in Q if not ((isinstance(q, list) and not Q.append(len(q)) and not Q.extend(q)) or (hasattr(q, '__dict__') and not Q.extend(q.__dict__.values()))))).reverse()
    
    def binary(self, o):
        Q = self.compact(o)
        return (struct.pack("<?",q) if isinstance(q,bool) else struct.pack("<d",q) if isinstance(q, float) else struct.pack("<i",q) if isinstance(q, int) else q.encode('utf-8') + b'\x00' for q in Q)


class VActFormatOIC:
    def _is_particle(self, context):
        return (context.show_self
            and context.parent
            and context.parent.original.select_get())
         
    def _resolve_trace(self, collection, trace, root):
        for parent in bpy.data.collections:
            if collection.name in parent.children.keys():
                trace.append(parent.name)
                if parent.name == root: return
                self._resolve_trace(parent, trace, root)
                return
            
    def _resolve_settings(self, settings):
        if settings.vact_axis in {'E'}:
            settings._up = 'Z'
            settings._forward = 'X'
        elif settings.vact_axis in {'T', 'Y'}:
            settings._up = 'Y'
            settings._forward = 'Z'
        elif settings.vact_axis in {'U'}:
            settings._up = 'Y'
            settings._forward = '-Z'
        elif settings.vact_axis in {'B'}:
            settings._up = 'Z'
            settings._forward = '-Y'
        else :
            settings._up = 'Z'
            settings._forward = 'Y'
    
    def _to_axis(self, P, Q, S, settings):
        if settings.vact_axis in {'U'}:
            # RH Zu nYf -> LH Yu Zf
            Q.conjugate()
            #Q = Q @ mathutils.Quaternion((0.0, 0.0, 1.0), math.radians(-180.0))
            P = mathutils.Vector([-P.x + 0, P.z + 0, -P.y + 0])
            Q = mathutils.Quaternion([Q.x + 0, Q.z + 0, Q.y + 0, Q.w + 0])
            S = mathutils.Vector([S.x + 0, S.z + 0, S.y + 0])
        elif settings.vact_axis in {'T'}:
            # RH Zu nYf -> RH Yu Zf
            P = mathutils.Vector([P.x + 0, P.z + 0, -P.y + 0])
            Q = mathutils.Quaternion([Q.x + 0, Q.z + 0, -Q.y + 0, Q.w + 0])
            S = mathutils.Vector([S.x + 0, S.z + 0, S.y + 0])
        elif settings.vact_axis in {'E'}:
            # RH Zu nYf -> LH Zu Xf
            Q.conjugate()
            ## TODO needs fixing
            P = mathutils.Vector([P.z + 0, -P.y + 0, P.x + 0])
            Q = mathutils.Quaternion([Q.z + 0, Q.y + 0, Q.x + 0, Q.w + 0])
            S = mathutils.Vector([S.z + 0, S.y + 0, S.x + 0])
        elif settings.vact_axis in {'Y'}:
            # RH Zu nYf -> LH Yu Zf
            Q.conjugate()
            P = mathutils.Vector([-P.x + 0, P.z + 0, -P.y + 0])
            Q = mathutils.Quaternion([Q.x + 0, Q.z + 0, Q.y + 0, Q.w + 0])
            S = mathutils.Vector([S.x + 0, S.z + 0, S.y + 0])
        elif settings.vact_axis in {'B'}:
            # RH Zu nYf -> RH Zu nYf
            pass
        
        return P, Q, S

    def _to_transform(self, context, cursor, settings):
        _Q = P = Q = S = None

        if not context:
            P = mathutils.Vector.Fill(3, 0)
            Q = mathutils.Quaternion()
            S = mathutils.Vector.Fill(3, 1)
        else:
            (P, Q, S) = context.matrix_world.decompose()
        
        _Q = Q  
        P, Q, S = self._to_axis(P, Q, S, settings)
        
        if settings.transform_format in {'PQS'}:
            return [ list(P), list(Q) , list(S) ]
        if settings.transform_format in {'PRS'}:
            E = _Q.to_euler()
            return [ list(P), list(E), list(S) ]
        if settings.transform_format in {'PQ'}:
            return [ list(P), list(Q.to_euler()) ]
        if settings.transform_format in {'PR'}:
            E = _Q.to_euler()
            return [ list(P), list(E) ]
        if settings.transform_format in {'PS'}:
            return [ list(P), list(S) ]
        if settings.transform_format in {'P'}:
            return P
        
    def _export_as(self, context, base, settings):
        _filepath = os.path.join(base,context)
        if settings.export_as in {'FBX'}:
            bpy.ops.export_scene.fbx(
                filepath=_filepath,
                check_existing=settings.use_overwrite_existing,
                use_selection=True,
                use_mesh_modifiers=False,
                use_custom_props=True,
                bake_space_transform=True,
                object_types={'MESH', 'ARMATURE', 'EMPTY'},
                mesh_smooth_type='FACE',
                apply_scale_options='FBX_SCALE_ALL',
                apply_unit_scale=True,
                bake_anim_force_startend_keying=False,
                bake_anim_use_nla_strips=False,
                bake_anim_use_all_actions=settings.use_skel_armatures,
                axis_forward= settings._forward,
                axis_up= settings._up)
        elif settings.export_as in {'GLB'}:
            bpy.ops.export_scene.gltf(
                filepath=_filepath,
                check_existing=settings.use_overwrite_existing,
                export_format='GLB',
                use_selection=True,
                ui_tab='GENERAL',
                export_draco_mesh_compression_enable=True,
                export_nla_strips=True,
                export_frame_range=False,
                export_animations=settings.use_skel_armatures,
                export_yup= settins._up in {'Y'},
                export_apply=True)
            
    def resolve_link(self, context, settings):
        collection = context.users_collection[0]
        trace = []
        
        ext = ".bin"
        if settings.export_as in {'FBX'}: ext = ".fbx"
        elif settings.export_as in {'GLB'}: ext = ".glb"
            
        if not settings.use_flat_export:
            trace.append(collection.name)
            self._resolve_trace(collection, trace, settings.root)
            trace.reverse()
        
        name = context.name
        if settings.use_lod_objects: name = name.replace("_LOD0","")
        
        _link = VActOIC.Link()
        _link.file = os.path.join('\\'.join(trace), name + ext)
        _link.type = settings.export_as
        return _link
    
    def resolve_meta(self, context, settings):
        meta = []
        for entry in context.vact_meta:
            if not entry.vact_enabled: continue
            property = VActOIC.Property()
            property._type = entry.vact_type
            property.name = entry.vact_name
            property.value = getattr(entry, entry.vact_ctx)
            meta.append(property)
        return meta
    
    def to_lod_group(self, context, name, lods, settings):
        into = "_LOD_GROUPS";
        _name = name.replace("_LOD0", "_LODS")
        group = bpy.data.objects.get(_name)
        if group: return group
        group = bpy.data.objects.new(_name, None)
        group['fbx_type'] = "LodGroup"
        
        for lod in lods:
            lod.parent = group
        
        collection = bpy.data.collections.get(into)
        if not collection:
            collection = bpy.data.collections.new(into)
            bpy.context.scene.collection.children.link(collection)
            
        collection.objects.link(group)
        
        return group
            
    def to_link(self, context, link, settings):
        base_directory = os.path.dirname(bpy.data.filepath)
        _filepath = ""
        _directory = ""
        
        if link.is_relative:
            _filepath = link.file
            _directory = os.path.dirname(os.path.relpath(link.file))
        else:
            _filepath = os.path.join(settings.directory_path, link.file)
            _directory = os.path.dirname(os.path.abspath(link.file))
        
        os.makedirs(os.path.join(base_directory,_directory), exist_ok=True)
        
        modifiers = []
        for modifier in context.modifiers:
            b_disable = (modifier.type in ['PARTICLE_SYSTEM']
                and modifier.show_render)
            if b_disable:
                modifiers.append(modifier)
                modifier.show_render = False 
        
        context.select_set(True)
        
        _name = context.data.name if context.data else context.name
        
        if settings.use_lod_objects:
            bpy.ops.object.select_pattern(pattern=_name.replace("_LOD0", "_LOD[1-9]*"), extend=True);
            if settings.use_lod_groups:
                group = self.to_lod_group(context, _name, bpy.context.selected_objects, settings)
                group.select_set(True)
        
        if settings.use_ucx_collisions:
            _prefix_name = _name.replace("_LOD0","")
            bpy.ops.object.select_pattern(pattern="UCX_" + _prefix_name, extend=True);
            bpy.ops.object.select_pattern(pattern="UCP_" + _prefix_name, extend=True);
            bpy.ops.object.select_pattern(pattern="USP_" + _prefix_name, extend=True);
            bpy.ops.object.select_pattern(pattern="UBX_" + _prefix_name, extend=True);
            
        if settings.use_skel_armatures:
            bpy.ops.object.select_pattern(pattern="SKEL_" + _name.replace("_LOD0","").replace("SK_","").replace("SM_",""), extend=True);
        
        self._export_as(_filepath, base_directory, settings)
        
        for selected in bpy.context.selected_objects:
            selected.select_set(False)
            
        for modifier in modifiers:
            modifier.show_render = True
    
    def from_array_modifiers(self, context, modifier, oic, cursor, settings):
        return []
    
    def from_depsgraph(self, context, oic, cursor, settings):
        depsgraph = context.evaluated_depsgraph_get()
     
        for instance in depsgraph.object_instances:
            b_skip_lod = "_LOD[1-9][0-9]" in instance.object.name
            b_skip_ucx = ("UCX_" in instance.object.name
                or "UCP_" in instance.object.name
                or "USP_" in instance.object.name
                or "UBX_" in instance.object.name)
            b_skip_empty = not settings.use_empty_objects and instance.object.type in {'EMPTY'}
            b_take_part = (not b_skip_empty and not b_skip_lod and not b_skip_ucx 
                and (instance.show_self
                and instance.object.original.select_get())
                or (settings.use_particle_systems
                and self._is_particle(instance)))
            
            if not b_take_part: continue
            
            idol = bpy.data.objects[instance.object.original.data.name if instance.object.original.data else instance.object.original.name]
            self.from_idol(instance, idol, oic, cursor, settings)
        
    def from_idol(self, context, idol, oic, cursor, settings):        
        _name = idol.data.name if idol.data else idol.name
        _object = None
        
        if not _name in cursor.objects:
            _link = self.resolve_link(idol, settings)
            _object = VActOIC.Object()
            _object.name = _name
            _object.link = _link
            _object.meta = self.resolve_meta(idol, settings)
            oic.add_object(_object)
            cursor.links.append((_link, idol))
            cursor.objects[_name] = _object.id
        else:
            _object = oic.objects[cursor.objects[_name]]
        
        _instance = VActOIC.Instance()
        _instance.object = _object.id
        _instance.transform = self._to_transform(context, cursor, settings)
        oic.add_instance(_instance)
        
        b_instance_meta = settings.use_instance_meta and not context.is_instance
        if b_instance_meta:
            _subject = bpy.data.objects[context.object.name]
            _entry = VActOIC.Entry()
            _entry.id = _instance.id
            _entry.meta = self.resolve_meta(_subject, settings)
            if _entry.meta: cursor.instance_meta.append(_entry)
    
    def from_item(self, context, oic, cursor, settings):
        if context.type in {'MESH'}:
            self.from_idol(context, context, oic, cursor, settings)
        
        for modifier in context.modifiers:
            if modifier in {'ARRAY'}:
                from_array_modifier(context, modifier, oic, cursor, settings)
    
    def from_root(self, context, oic, cursor, settings):
        oic._format = settings.oic_format
        oic.transform = self._to_transform(None, cursor, settings)
        oic.topology = settings.transform_format
        oic.axis = settings.vact_axis
        self.from_depsgraph(context, oic, cursor, settings)
        return oic
    
    def do_export_normal(self, context, filepath):
        with open(filepath, "w", encoding='utf-8') as file:
            json.dump(context, file, cls=_VAct_OICEncoder)
            file.close()
    
    def do_export_compact(self, context, filepath):
        with open(filepath+"c", "w", encoding='utf-8') as file:
            encoder = _VAct_OICEncoder()
            for entity in encoder.compact(context): file.write(json.dumps(entity)+" ")
            file.close()
            
    def do_export_binary(self, context, filepath):
        with open(filepath+"b", "wb") as file:
            encoder = _VAct_OICEncoder()
            for bytes in encoder.binary(context): file.write(bytes)
            file.close()
        
    def do_export(self, context, filepath, settings):
        self._resolve_settings(settings)
        
        layer = bpy.context.view_layer
        active = layer.objects.active
        selections = bpy.context.selected_objects        
        
        cursor = _VAct_OICCursor()
        oic = self.from_root(bpy.context, VActOIC(settings.object_name), cursor, settings)
        meta = cursor.instance_meta
        
        if settings.oic_format in {'JSON'}:
            self.do_export_normal(oic, filepath)
            if cursor.instance_meta: self.do_export_normal(meta, filepath+"m")
        elif settings.oic_format in {'PACK'}:
            self.do_export_compact(oic, filepath)
            if cursor.instance_meta: self.do_export_compact(meta, filepath+"m")
        elif settings.oic_format in {'BIN'}:
            self.do_export_binary(oic, filepath)
            if cursor.instance_meta: self.do_export_binary(meta, filepath+"m")
        else: raise Exception("Invalid OIC format selected")
        
        if settings.use_export_objects:
            bpy.ops.object.select_all(action='DESELECT')
            for (link, item) in cursor.links: self.to_link(item, link, settings)
                
            layer.objects.active = active
            for selected in selections: selected.select_set(True)
        
        return {'FINISHED'}
    
    def do_import(self, context, filepath, settings):
        with open(filepath, 'r', encoding='utf-8') as file:
            oic = json.load(file, cls=_VAct_OICEncoder)
            file.close()
        
        return {'FINISHED'}


from bpy_extras.io_utils import (
    ExportHelper,
    ImportHelper
)

from bpy.types import (
    UIList,
    Menu,
    Panel,
    Operator,
    PropertyGroup
)

from bpy.props import (
    IntProperty, 
    EnumProperty, 
    StringProperty, 
    FloatProperty, 
    CollectionProperty, 
    BoolProperty
)

class VActHelper(PropertyGroup):
    @classmethod
    def register_menu(cls, self, context):
        self.layout.operator(cls.bl_idname, text=cls.bl_label)


class VActFormatOICHelper(VActHelper):
    is_import = False
    filename_ext = ".oic"
    
    filter_glob : StringProperty(default="*.oic;*.oise;*.ois;*.oicb;*.oicc;*.oie;", options={'HIDDEN'}, maxlen=255)
    use_particle_systems : BoolProperty(name="Use Particle Systems", default=True)
    use_geometric_nodes : BoolProperty(name="Use Geometric Nodes", default=True)
    #use_array_modifiers : BoolProperty(name = "Use Array Modifiers", default=False)
    #use_sub_systems : BoolProperty(name = "Use OIC Sub Systems", default=False)
    use_skel_armatures : BoolProperty(name="Use SKEL", default=False)
    use_ucx_collisions : BoolProperty(name="Use UCX", default=True)
    use_lod_objects : BoolProperty(name="Use LOD", default=True)
    use_lod_groups : BoolProperty(name="Use LOD Groups", default=False)
    use_instance_meta : BoolProperty(name="Use Instance Meta", default=False)
    #use_light_objects : BoolProperty(name="Export Lights", default=True)
    use_empty_objects : BoolProperty(name="Export Empties", default=True)
    use_export_objects : BoolProperty(name="Export Objects", default=True, description = "Export the objects, not only composition info")
    use_overwrite_existing : BoolProperty(name="Overwrite Existing", default=True)
    use_flat_export : BoolProperty(name="Flat Export", default=False)
    
    @classmethod
    def register_menu(cls, self, context):
        self.layout.operator(cls.bl_idname, text=cls.bl_label)


class VActExportOICSettings(VActFormatOICHelper):
    bl_menu = "TOPBAR_MT_file_export"
        
    root : StringProperty(name="Root Collection", default="Assets")
    object_name : StringProperty(name="Name", default=bpy.path.display_name_from_filepath(bpy.data.filepath))
    directory_path : StringProperty(options={'HIDDEN'}, default="")
    
    oic_format : EnumProperty(
        name="OIC Format",
        description="Select OIC Export Format",
        items=(
            ('JSON', "Json", "Save as Json File"),
            ('PACK', "Compact", "Export as Compact List"),
            ('BIN', "Binary", "Export as Binary"),
        ),
        default='JSON'
    )
    
    export_as : EnumProperty(
        name="Export As",
        description="Select Object Link Type",
        items=(
            ('FBX', "FBX", "Autodesk Filmbox format"),
            ('GLB', "GLB", "Graphics Language Transmission Format 2.0"),
        ),
        default='FBX'
    )
    
    transform_format : EnumProperty(
        name="Transform",
        description="Select Your Transofmration Format",
        items=(
            ('P', "Position", "Position"),
            ('PS', "PS", "Position Scale"),
            ('PR', "PR", "Position Rotation"),
            ('PQ', "PQ", "Position Quatertion"),
            ('PQS', "PQS", "Position Quatertion Scale"),
            ('PRS', "PRS", "Position Rotation Scale"),
        ),
        default='PQS'
    )

    vact_axis : EnumProperty(
        name="Axis System",
        description="Select Your Axis System",
        items=(
            ('U', "Unity", "As Unity Axis"),
            ('B', "Blender", "As Blender Axis"),
            ('T', "TreeJS", "As TreeJS Axis"),
            ('E', "Unreal Engine", "As Unreal Engine Axis"),
            ('Y', "BabylonJs", "As BabylonJs Axis"),
        ),
        default='U'
    )


class VActImportOICSettings(VActFormatOICHelper):
    bl_menu = "TOPBAR_MT_file_import"


class ExportOIC(Operator, ExportHelper, VActFormatOIC, VActExportOICSettings):
    """Vivacity Interactive Export Object Instance Composition (OIC)"""
    bl_idname = "vact.export_oic"
    bl_label = "Export Object Instance Composition (OIC)"

    def execute(self, context):
        return self.do_export(context, self.filepath, self)

    
class ImportOIC(Operator, ImportHelper, VActFormatOIC, VActImportOICSettings):
    """Vivacity Interactive Import Object Instance Composition (OIC)"""
    bl_idname = "vact.import_oic"
    bl_label = "Import Object Instance Composition (OIC)"

    def execute(self, context):
        return self.do_export(context, self.filepath, self)


class VActProperty(PropertyGroup):
    def get_ctx(self):
        return 'vact_' + self.vact_type
    
    def set_value(self, value):
        self[self.vact_ctx] = value

    def get_value(self):
        return self[self.vact_ctx]

    vact_ctx : StringProperty(name="Context", default= "", options={'HIDDEN', 'LIBRARY_EDITABLE'}, get=get_ctx)
    
    vact_icon : StringProperty(name="Icon", default= "QUESTION", options={'HIDDEN', 'LIBRARY_EDITABLE'})
    vact_type : StringProperty(name="Type", default= "", options={'HIDDEN', 'LIBRARY_EDITABLE'}, maxlen=1)
    vact_name : StringProperty(name="Name", default="_Nameless", options={'LIBRARY_EDITABLE'})
    vact_enabled : BoolProperty(name="Enabled", default=True, options={'LIBRARY_EDITABLE'})

    vact_s : StringProperty(name="String", default="_Value", options={'HIDDEN', 'LIBRARY_EDITABLE'})
    vact_i : IntProperty(name="Int", default=0, options={'HIDDEN', 'LIBRARY_EDITABLE'})
    vact_f : FloatProperty(name="Float", default=1.0, options={'HIDDEN', 'LIBRARY_EDITABLE'})
    vact_b : BoolProperty(name="Bool", default=True, options={'HIDDEN', 'LIBRARY_EDITABLE'})


class VActMeta:
    @classmethod
    def meta(cls, context=None):
        return context.object if context else bpy.context.object
    
    @classmethod
    def entry(cls, context=None):
        meta = cls.meta(context)
        return meta.vact_meta[meta.vact_meta_index]
    
    @classmethod
    def entry_add(cls, context=None):
        meta = cls.meta(context)
        return meta.vact_meta.add()
    
    @classmethod
    def entry_remove(cls, context=None, target=None):
        meta = cls.meta(context)
        meta.vact_meta.remove(meta.vact_meta_index)
        meta.vact_meta_index -= 1

    @classmethod
    def entry_poll(cls, context=None):
        meta = cls.meta(context)
        return bool(meta) and bool(meta.vact_meta) and meta.vact_meta_index < len(meta.vact_meta)
    
    @classmethod
    def entry_selected(cls, index, context):
        meta = cls.meta(context)
        return index == meta.vact_meta_index


class VActPropertyHelper(VActHelper):
    bl_menu = None


class VACTPROPERTY_OT_Delete(Operator, VActPropertyHelper):
    """Delete Property"""
    bl_idname = "vact.delete_property"
    bl_label = "Delete"

    def execute(self, context):
        VActMeta.entry_remove(context)
        return {'FINISHED'}


class VACTPROPERTY_OT_String_New(Operator, VActPropertyHelper):
    """Create String Property"""
    bl_idname = "vact.new_property_string"
    bl_label = "String"
    bl_icon = 'EVENT_S'

    def execute(self, context):
        entry = VActMeta.entry_add(context)
        entry.vact_name = "MyString"
        entry.vact_type = "s"
        entry.vact_icon = self.bl_icon
        return {'FINISHED'}

class VACTPROPERTY_OT_Int_New(Operator, VActPropertyHelper):
    """Create Int Property"""
    bl_idname = "vact.new_property_int"
    bl_label = "Int"
    bl_icon = 'EVENT_I'

    def execute(self, context):
        entry = VActMeta.entry_add(context)
        entry.vact_name = "MyInt"
        entry.vact_type = "i"
        entry.vact_icon = self.bl_icon
        return {'FINISHED'}

class VACTPROPERTY_OT_Float_New(Operator, VActPropertyHelper):
    """Create Float Property"""
    bl_idname = "vact.new_property_float"
    bl_label = "Float"
    bl_icon = 'EVENT_F'

    def execute(self, context):
        entry = VActMeta.entry_add(context)
        entry.vact_name = "MyFloat"
        entry.vact_type = "f"
        entry.vact_icon = self.bl_icon
        return {'FINISHED'}

class VACTPROPERTY_OT_Bool_New(Operator, VActPropertyHelper):
    """Create Bool Property"""
    bl_idname = "vact.new_property_bool"
    bl_label = "Bool"
    bl_icon = 'EVENT_B'

    def execute(self, context):
        entry = VActMeta.entry_add(context)
        entry.vact_name = "MyBool"
        entry.vact_type = "b"
        entry.vact_icon = self.bl_icon
        return {'FINISHED'}

class VACTMETA_PT:
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "object"
    bl_options = {"DEFAULT_CLOSED"}


class VACTPROPERTY_UL_List(UIList):
    """Property List"""
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        _icon = icon if item.vact_icon is None else item.vact_icon
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            b_val_bool = item.vact_type in {'b'}
            b_selected = VActMeta.entry_selected(index, context)

            _val_text = str(item.vact_b) if b_val_bool else ""
            _val_emboss = 'NORMAL' if b_selected else 'NONE' 
            _val_align = 'CENTER' if b_val_bool else 'LEFT'
            _val_x = 16

            row = layout.row()
            sub = row.row(align=True)
            sub.prop(item, 'vact_name', icon=_icon, text="", emboss=b_selected)
            val = sub.row(align=True)
            val.prop(item, item.vact_ctx, text=_val_text, emboss=b_selected)
            val.ui_units_x = _val_x
            val.emboss = _val_emboss
            #sub.alignment = _val_align
            sub.enabled = item.vact_enabled
            row.prop(item, 'vact_enabled', text="")
            row.enabled = b_selected
                
        if self.layout_type in {'GRID'} :
            layout.alignment = 'CENTER'
            layout.label(text="", icon = _icon)


class VACTPROPERTY_MT_Add_Property(Menu):
    """VAct Add Properties Menu"""
    bl_label = "Add New"
    bl_idname = "VACTPROPERTY_MT_Add_Property"

    def draw(self, context):
        layout = self.layout
        layout.operator("vact.new_property_string", icon='EVENT_S')
        layout.operator("vact.new_property_int", icon='EVENT_I')
        layout.operator("vact.new_property_float", icon='EVENT_F')
        layout.operator("vact.new_property_bool", icon='EVENT_B')


class VACTMETA_PT_Main(VACTMETA_PT, Panel):
    """Meta Data Control Panel"""
    bl_label = "Meta Data"
    bl_idname = "VACTMETA_PT_Main"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        meta = VActMeta.meta(context)
        
        row = layout.row()
        col = row.column()
        col.template_list('VACTPROPERTY_UL_List', "", meta, "vact_meta", meta, "vact_meta_index")
        col = row.column(align=True)
        col.menu('VACTPROPERTY_MT_Add_Property', text='', icon='ADD')
        col.operator("vact.delete_property", text="", icon='REMOVE')
        layout.separator()
        
        if VActMeta.entry_poll(context):
            entry = VActMeta.entry(context)
            b_val_bool = entry.vact_type in {'b'}
            _val_text = str(entry.vact_b) if b_val_bool else ""
            _val_align = 'CENTER' if b_val_bool else 'EXPAND'

            row = layout.row(align=True)
            col = row.column(align=True)
            col.prop(entry,"vact_name")
            row = layout.row()
            row.prop(entry, entry.vact_ctx, text=_val_text)
            row.alignment = _val_align
            
            row.enabled = col.enabled = entry.vact_enabled


operators = (
    ImportOIC,
    ExportOIC,
    VACTPROPERTY_OT_Delete,
    VACTPROPERTY_OT_String_New,
    VACTPROPERTY_OT_Int_New,
    VACTPROPERTY_OT_Float_New,
    VACTPROPERTY_OT_Bool_New
)

classes = (
    VActHelper,
    VActProperty,
    VActPropertyHelper,
    VActFormatOICHelper,
    VActImportOICSettings,
    VActExportOICSettings,
    VACTPROPERTY_UL_List,
    VACTPROPERTY_MT_Add_Property,
    VACTMETA_PT_Main
) + operators

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
        
    for ops in operators:
        if ops.bl_menu:
            getattr(bpy.types,ops.bl_menu).append(ops.register_menu)
    
    bpy.types.Object.vact_meta = CollectionProperty(name="Meta Data", type=VActProperty)
    bpy.types.Object.vact_meta_index = IntProperty(name="Meta Index", default=0, min=0)

def unregister():
    for ops in operators:
        if ops.bl_menu:
            getattr(bpy.types,ops.bl_menu).remove(ops.register_menu)
        
    for cls in classes:
        bpy.utils.unregister_class(cls)

    del bpy.types.Object.vact_meta


if __name__ == "__main__":
    register()