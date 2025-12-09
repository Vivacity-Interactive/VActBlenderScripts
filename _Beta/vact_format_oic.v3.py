import bpy, json, mathutils, math, itertools, os, struct, sys, re, typing

from bpy_extras import (
    io_utils
)

from collections import (
    deque
)

class VActCheckAny:
    def __init__(self, checks, default = None):
        self.default = default
        self.checks = checks

    def get(self, index):
        for check in self.checks:
            data = check.get(index)
            if data: return data
        return self.default

class VActCheckContains:
    def __init__(self, data, substring, default = None):
        self.default = default
        self.substring = substring
        self.data = data

    def get(self, index):
        return self.data if self.substring in index else self.default
    
class VActCheckRegex:
    def __init__(self, data, regex):
        self.default = default
        self.regex = regex if isinstance(regex, typing.Pattern) else re.compile(regex)
        self.data = data

    def get(self, index):
        return self.data if self.regex.match(index) in index else self.default

class _VAct_OICCursor:
    def __init__(self):
        self.into_assets = None
        self.idols = {}
        self.exclude = set()
        self.metas = []
        self.axis = mathutils.Matrix.Identity(4)
        self.hlpr = None

class VActExportEntry:
    def __init__(self, type = "Mesh", dir = "/Game/", tmpl = "$1.$1"):
        self.type = type
        self.dir = dir
        self.tmpl = tmpl

    def path(self, name, module = "Engine", dir = ""):
        #("Mesh", "/Game/Models/", "$1.$1"),
        return self.dir + self.tmpl.replace('$1', name).replace('$2', module).replace('$3', dir)

class VActExportRule:
    def __init__(self, axis, identity, rvalid, rclean, rfix, map, mdefault, stmpl, genx, lut = {}):
        self.lut = lut or {}
        self.rvalid = rvalid if isinstance(rvalid, typing.Pattern) else re.compile(rvalid)
        self.rclean = rclean if isinstance(rclean, typing.Pattern) else re.compile(rclean)
        self.rfix = rfix if isinstance(rfix, typing.Pattern) else re.compile(rfix)
        self.map = map or {}
        self.axis = axis
        self.prefix = identity
        self.mdefault = mdefault if isinstance(mdefault, VActExportEntry) else VActExportEntry()
        self.stmpl = stmpl
        self.genx = genx
    
    def convert(self, decomp, b_other = False):
        if b_other: return decomp[0] + decomp[1].upper() + decomp[2].upper() + decomp[3].upper() + decomp[4].title() + decomp[7].upper() + decomp[9]
        else: return decomp[0] + decomp[1] + decomp[2] + decomp[3] + decomp[4] + decomp[7] + decomp[9]
    
    def clean(self, name, sub=""):
        return self.rclean.sub(sub, name) if self.rclean else None
    
    def fix(self, name, sub="_"):
        return self.rfix.sub(sub, name) if self.rfix else None
    
    def pretty(self, name, b_lut = False):
        if not self.rvalid: return None
        _match = self.rvalid.match(name)
        _decomp = None
        _name = None
        if _match:
            #_SOCKET_UCX_SM_MYNIC_2_7XL_EOBJECT_223_LOD2_12
            #(_, SOCKET_, UCX_, SM_, (MYNIC_2_7XL_EOBJECT_223, _223, 223), (_LOD2, 2), (_12, 12))
            #(1, 2, 3, 4, (5, 6, 7), (8, 9), (10, 11))
            _decomp = (
                (_match.group(1) or ""),
                (_match.group(2) or "").upper(),
                (_match.group(3) or "").upper(),
                (_match.group(4) or "").upper(),
                (_match.group(5) or "").title(),
                _match.group(6) or "",
                int(_match.group(7) or "-1"),
                (_match.group(8) or "").upper(),
                int(_match.group(9) or "-1"),
                _match.group(10) or "",
                int(_match.group(11) or "-1")
            )
            _name = self.convert(_decomp, False)
        return _name, _decomp
    
    def script(self, name, module = "Engine", dir = ""):
        _dir = self.lut.get(name) or dir
        return self.stmpl.replace('$1', name).replace('$2', module).replace('$3', _dir)
    
    def asset(self, name, b_particle = False, module = "", dir = "", b_lut = False):
        _asset = None
        _type = None
        entry = None
        name, decomp = self.pretty(name, b_lut)
        if name:
            #print(decomp[3])
            entry = self.map.get(decomp[3], self.mdefault)
            _type = 'Particle' if b_particle else entry.type
            if entry: _asset = entry.path(name, module, dir)
        
        return _asset, _type, name, entry, decomp

class _VActERUE(VActExportRule):
    def __init__(self, lut = {}):
        super().__init__(
            "UnrealEngine",
            "UE",
            '^(_+)?(SOCKET_)?(U(?:CX|BX|CP|SP|CY)_)?(SM_|SKEL_|M_|T_|AS_|ABP_|FXS_|AUDIO_|WDS_|PPV_|OIC_|PGX_|MUSIC_|DIALO_|AMBIA_|HINT_|SK_|RIG_|E_|MA_|L_|LP_|LR_|LS_|LE_|LD_|LM_|C_|CLOTH_|DAT_|DT_|BP_|CT_|ABP_)?([_a-zA-Z0-9]+?(_(\d+))?)(?:(_LOD(\d+))?(_(\d+))?$)',
            '[-+ .()\[\]]+',
            '[-+ .]+',
            {
                'SM_': VActExportEntry("Mesh", "/Game/Models/", "$3$1.$1"),
                'BP_': VActExportEntry("Actor", "/Game/Blueprints/", "$3$1.$1"),
                'HINT_': VActExportEntry("Actor", "/Script/", "$2.$1"),
                'E_': VActExportEntry("Actor", "/Script/", "$2.$1"),
                'SKEL_': VActExportEntry("Mesh", "/Game/Models/Actors/", "$1_Skeleton.$1_Skeleton"), # assuming a skeletal mesh is also a mesh
                'SK_': VActExportEntry("Mesh", "/Game/Models/Actors/", "$1.$1"),
                'RIG_': VActExportEntry("Mesh", "/Game/Models/Actors/", "$1.$1"),
                'MUSIC_': VActExportEntry("Audio", "/Game/Audio/Music/", "$1.$1"),
                'AUDIO_': VActExportEntry("Audio", "/Game/Audio/Sound/", "$3$1.$1"),
                'AMBIA_': VActExportEntry("Audio", "/Game/Audio/Ambiance/", "$1.$1"),
                'DIALO_': VActExportEntry("Audio", "/Game/Audio/Dialogue/", "$3$1.$1"),
                'MA_': VActExportEntry("Actor", "/Script/", "$2.$1"),
                'T_': VActExportEntry("Data", "/Game/Textures/", "$3$1.$1"),
                'M_': VActExportEntry("Data", "/Game/Materials/", "$1.$1"),
                'MI_': VActExportEntry("Data", "/Game/Materials/", "$1.$1"),
                'AS_': VActExportEntry("Data", "/Game/Models/Actors/", "$3$1.$1"),
                'ABP_': VActExportEntry("Data", "/Game/Models/Actors/", "$3$1.$1"),
                'FXS_': VActExportEntry("System", "/Game/Effects/", "$3$1.$1"),
                'CLOTH_': VActExportEntry("System", "/Game/Models/", "$3$1.$1"),
                'L_': VActExportEntry("Actor", "/Script/", "Engine.PointLight"),
                'LP_': VActExportEntry("Actor", "/Script/", "Engine.PointLight"),
                'LR_': VActExportEntry("Actor", "/Script/", "Engine.RectLight"),
                'LS_': VActExportEntry("Actor", "/Script/", "Engine.SpotLight"),
                'LE_': VActExportEntry("Actor", "/Script/", "Engine.SkyLight"),
                'LD_': VActExportEntry("Actor", "/Script/", "Engine.DirectionalLight"),
                'LM_': VActExportEntry("Actor", "/Script/", "Engine.GeneratedMeshAreaLight"),
                'C_': VActExportEntry("Actor", "/Script/", "Engine.GeneratedMeshAreaLight"),
                'CC_': VActExportEntry("Actor", "/Script/", "CinematicCamera.CineCameraActor"),
                'OIC_': VActExportEntry("Data", "/Game/Blueprints/OICProfiles/", "$1.$1"),
                'PGX_': VActExportEntry("Data", "/Game/Blueprints/PGXProfiles/", "$1.$1"),
                'WDS_': VActExportEntry("Actor", "/Script/", "Engine.WindDirectionalSource"),
                'PPV_': VActExportEntry("Actor", "/Script/", "Engine.PostProcessVolume")
            },
            VActExportEntry("Mesh", "/Game/", "$1.$1"),
            "/Script/$2.$1",
            {"GX_"},
            lut
        )

def _vact_resolve_hlpr(axis, lut = {}):
    #if axis in {'UnrealEngine'}: return _VActERUE(lut)
    #elif axis in {'TreeJS', 'BabylonJs'}: return _VActERWeb(lut)
    #elif axis in {'Unity'}: return _VActERUnity(lut)
    #elif axis in {'Blender'}: return _VActERBlender(lut)
    return _VActERUE(lut)

def _vact_hash(obj, flag, szf=1):
    return (id(obj) << szf) | int(flag)

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
    
class VActName(str):
    def __str__(self):
        return str(self) + ''
    
    def __repr__(self):
        return self.__str__()

class VActIdol:
    def __init__(self):
        self.oic = None
        self.object = None
        self.name = None
        self.type = None
        self.asset = None
        self.entry = None
        self.decomp = None
        self.eval_obj = None
        self.eval_geom = None
        self.b_cloud = False
        self.b_ignore = False
        self.b_jump = False
        self.cloud = None
        self.refs = None
                

class VActOIC:
    class Property:
        def __init__(self):
            self.name = "_Unknown"
            self.type = "_Unknown"
            self.value = None
        
        def json(self):
            _fval = str if self.type not in {'String'} else json.dumps
            _value = f"({','.join(map(_fval, self.value))})" if isinstance(self.value, tuple) else _fval(self.value)
            return f"{self.name}:{_value}"
        
        def compact(self):
            return self.json()
        
        def binary(self):
            pass
            #struct.pack("<?",q) bool
            #struct.pack("<d",q) float
            #struct.pack("<i",q) int
            #q.encode('utf-8') + b'\x00' string
            #_value = (b'').join((x for ))
            #return self.name.encode('utf-8') + b'\x00' + _value

    class Instance:
        def __init__(self):
            self.id = -1
            self.object = -1
            self.parent = -1
            self.meta = -1
            self.transform = None

        def json(self):
            _transform = ','.join((f"({','.join(map(str, x))})" for x in self.transform))
            return f"({self.id},{self.object},{self.parent},{self.meta},({_transform}))"
        
        def compact(self):
            return self.json()
        
        def binary(self):
            pass
 
    class Object:
        def __init__(self):
            self.id = -1
            self.type = "_Unknown"
            self.asset = ""
            self.meta = -1

        def json(self):
            return f"{{Type:{self.type},Asset:{json.dumps(self.asset)},Meta:{self.meta}}}"
        
        def compact(self):
            return f"{{{self.type},{json.dumps(self.asset)},{self.meta}}}"
        
        def binary(self):
            pass

    class Link:
        def __init__(self):
            self.type = "_Unknown"
            self.file = ""
            self.object = None
    
    class Meta:
        def __init__(self):
            self.id = -1
            self.entries = []

        def add_entry(self, entry):
            self.entries.append(entry)
            return len(self.entries)
        
        def has(self):
            return len(self.entries) > 0
        
        def json(self):
            return f"[{','.join((x.json() for x in self.entries))}]"
        
        def compact(self):
            return self.json()
        
        def binary(self):
            pass
    
    class MetaEntry:
        def __init__(self):
            self.asset = "_Unknown"
            self.properties = []
        
        def add_property(self, property):
            self.properties.append(property)
            return len(self.properties)
        
        def has(self):
            return len(self.properties) > 0
        
        def json(self):
            _properties = f"{{{','.join((x.json() for x in self.properties))}}}"
            return f"{{Asset:{json.dumps(self.asset)},Properties:{_properties}}}"
        
        def compact(self):
            _properties = f"{{{','.join((x.compact() for x in self.properties))}}}"
            return f"{{{json.dumps(self.asset)},{_properties}}}"
        
        def binary(self):
            pass
    
    
    def __init__(self, name="_Nameless" ):
        self.type = "OIC"
        self.version = "v2"
        self.axis = "_Unknown"
        self.notes = ""
        self.title = name
        self.name = name
        self.objects = []
        self.instances = []
        self.metas = []
    
    def add_instance(self, item):
        item.id = len(self.instances)
        self.instances.append(item)
        return item.id
    
    def add_object(self, item):
        item.id = len(self.objects)
        self.objects.append(item)
        return item.id
    
    def add_meta(self, item):
        item.id = len(self.metas)
        self.metas.append(item)
        return item.id
    
    def optimize(self):
        pass

    def json(self):
        _objects = f"[{','.join((x.json() for x in self.objects))}]"
        _instances = f"[{','.join((x.json() for x in self.instances))}]"
        _metas = f"[{','.join((x.json() for x in self.metas))}]"
        return f"{{Type:{self.type},Version:{self.version},Axis:{self.axis},Notes:{json.dumps(self.notes)},Title:{json.dumps(self.title)},Name:{self.name},Objects:{_objects},Instances:{_instances},Metas:{_metas}}}"
    
    def compact(self):
        _objects = f"[{','.join((x.compact() for x in self.objects))}]"
        _instances = f"[{','.join((x.compact() for x in self.instances))}]"
        _metas = f"[{','.join((x.compact() for x in self.metas))}]"
        return f"{{{self.type},{self.version},{self.axis},{json.dumps(self.notes)},{json.dumps(self.title)},{self.name},{_objects},{_instances},{_metas}}}"
    
    def binary(self):
            pass

class _VActDummyInstance:
    def __init__(self):
        self.object = None
        self.matrix_world = mathutils.Matrix.Identity(4)

class VActFormatOIC:    
    def _to_axis(self, P, Q, S, cursor, settings):
        _scale = settings.scale_correct
        if settings.vact_axis in {'Unity', 'BabylonJs'}:
            # RH Zu nYf -> LH Yu Zf
            # Q.conjugate()
            # P = mathutils.Vector([P.x + 0, P.z + 0, -P.y + 0])
            # Q = mathutils.Quaternion([Q.w + 0, Q.x + 0, Q.z + 0, Q.y + 0])
            # S = mathutils.Vector([S.x + 0, S.z + 0, S.y + 0])
            Q.conjugate()
            P = mathutils.Vector([-P.x + 0, P.z + 0, -P.y + 0])
            Q = mathutils.Quaternion([Q.x + 0, Q.z + 0, Q.y + 0, Q.w + 0])
            S = mathutils.Vector([S.x + 0, S.z + 0, S.y + 0])
        elif settings.vact_axis in {'TreeJS'}:
            # RH Zu nYf -> RH Yu Zf
            P = mathutils.Vector([P.x + 0, P.z + 0, -P.y + 0])
            Q = mathutils.Quaternion([Q.w + 0, Q.x + 0, Q.z + 0, -Q.y + 0])
            S = mathutils.Vector([S.x + 0, S.z + 0, S.y + 0])
        elif settings.vact_axis in {'UnrealEngine'}:
            # RH Zu nYf -> LH Zu Xf
            #Q.conjugate()
            #Q = mathutils.Quaternion([Q.w + 0, Q.y + 0, Q.x + 0, Q.z + 0])
            Q = (Q @ mathutils.Quaternion((0.0, 0.0, 1.0), math.radians(90.0))).conjugated()
            P = mathutils.Vector([-P.y + 0, -P.x + 0, P.z + 0])
            #Q = mathutils.Quaternion([Q.x + 0, Q.y + 0, Q.z + 0, Q.w + 0])
            Q = mathutils.Quaternion([-Q.y + 0, -Q.x + 0, Q.z + 0, Q.w + 0])
            S = mathutils.Vector([S.y + 0, S.x + 0, S.z + 0])
        elif settings.vact_axis in {'Blender'}:
            # RH Zu nYf -> RH Zu nYf
            pass
        P = P * _scale
        return P, Q, S

    def _to_transform(self, context, cursor, settings):
        P = Q = S = None

        if not context:
            P = mathutils.Vector.Fill(3, 0)
            Q = mathutils.Quaternion()
            S = mathutils.Vector.Fill(3, 1)
        else:
            (P, Q, S) = context.matrix_world.decompose()
        
        P, Q, S = self._to_axis(P, Q, S, cursor, settings)
        return ( tuple(P), tuple(Q) , tuple(S) )
        
    def _export_as(self, context, base, settings):
        _filepath = os.path.join(base, context)
        if settings.export_as in {'FBX'}:
            bpy.ops.export_scene.fbx(
                filepath=_filepath,
                check_existing=settings.use_overwrite_existing,
                use_selection=True,
                use_mesh_modifiers=False,
                use_custom_props=True,
                bake_space_transform=True,
                object_types={'MESH', 'ARMATURE', 'EMPTY', 'OTHER'},
                mesh_smooth_type='FACE',
                apply_scale_options='FBX_SCALE_ALL',
                apply_unit_scale=True,
                bake_anim=settings.use_export_animation,
                bake_anim_force_startend_keying=settings.use_export_animation,
                bake_anim_use_nla_strips=False,
                bake_anim_use_all_actions=settings.use_export_animation,
                axis_forward= settings._forward,
                axis_up=settings._up,
                add_leaf_bones=False)
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
                export_animations=settings.use_export_animation,
                export_yup= settings._up in {'Y'},
                export_apply=True)
        # TODO maybe alambic supoort
            
    def resolve_link(self, context, cursor, settings): 
        ext = ".bin"
        if settings.export_as in {'FBX'}: ext = ".fbx"
        elif settings.export_as in {'GLB'}: ext = ".glb"
        _link = VActOIC.Link()
        _link.file = os.path.join(context.entry.dir, settings.asset_path, context.name + ext)
        _link.type = settings.export_as
        return _link
    
    def resolve_meta(self, context, cursor, settings):
        meta = VActOIC.Meta()
        for entry in context.vact_meta:
            if not entry.vact_enabled: continue
            meta_entry = VActOIC.MetaEntry()
            meta_entry.asset = cursor.hlpr.script(entry.vact_asset, settings.module_name)
            #print(('-enabled','meta_entry.asset',meta_entry.asset, context.name))
            for property in entry.vact_properties:
                if not property.vact_enabled: continue
                _property = VActOIC.Property()
                _property.type = property.vact_type
                _property.name = property.vact_name
                _property.value = getattr(property, property.vact_ctx)
                meta_entry.add_property(_property)
            meta.add_entry(meta_entry)
        return meta if meta.has() else None
    
    def from_geometryset(self, context, references, name, parent, id, depsgraph, oic, cursor, settings):
        _indicie = context.attributes[".reference_index"]
        _transforms = context.attributes["instance_transform"]
        _object = None
        _dumy = _VActDummyInstance()
        _base = parent.matrix_world if parent else mathutils.Matrix.Identity(4)
        for _index in range(len(context.points)):
            index = _indicie.data[_index].value
            _matrix = _dumy.matrix_world = (_base @ _transforms.data[_index].value)
            reference = references[index]
            if isinstance(reference, bpy.types.GeometrySet):
                _object = bpy.data.objects.get(reference.name)
                if _object:
                    #print(("-geomi", "geometryset", "object", reference.name, _object.name, _object.data.name))
                    idol = self.resolve_idol(_object, True, depsgraph, oic, cursor, settings, False)
                    _dumy.object = _object
                    _id = self.from_idol(_dumy, idol, True, id, oic, cursor, settings)
                    if idol.b_cloud: self.from_geometryset(idol.cloud, idol.refs, idol.name, _dumy, _id, depsgraph, oic, cursor, settings)
                
                _mesh = bpy.data.meshes.get(reference.mesh.name) if reference.mesh else None
                # TODO find out what to do when mesh is generated needs
                # b_generated = not _mesh and reference.mesh
                # if b_generated:
                #     _mesh = reference.mesh.to_mesh().copy()
                #     _mesh = reference.name or f"{name}_{_index}"
                
                if _mesh:
                    _object = bpy.data.objects.new(_mesh.name, _mesh)
                    #print(("-geomi", "geometryset", "mesh", reference.name, _object.name, _object.data.name))
                    idol = self.resolve_idol(_object, True, depsgraph, oic, cursor, settings, False)
                    _dumy.object = _object
                    _id = self.from_idol(_dumy, idol, True, id, oic, cursor, settings)
                    if idol.b_cloud: self.from_geometryset(idol.cloud, idol.refs, idol.name, _dumy, _id, depsgraph, oic, cursor, settings)
                    bpy.data.objects.remove(_object)
            elif isinstance(reference, bpy.types.Object):
                _object = bpy.data.objects.get(reference.name)
                if _object:
                    _dumy.object = _object
                    #print(('-geomi', 'object', reference.name, _object.name, _object.data.name))
                    idol = self.resolve_idol(_object, True, depsgraph, oic, cursor, settings, False)
                    _id = self.from_idol(_dumy, idol, True, id, oic, cursor, settings)
                    if idol.b_cloud: self.from_geometryset(idol.cloud, idol.refs, idol.name, _dumy, _id, depsgraph, oic, cursor, settings)
            elif isinstance(reference, bpy.types.Collection):
                #print(('-geomi', 'collection', reference.name))
                for child in reference.all_objects:
                    _dumy.matrix_world = _matrix @ child.matrix_world
                    _dumy.object = child
                    #print(("-geomi", 'collection', "child", reference.name, reference.data.name))
                    idol = self.resolve_idol(child, True, depsgraph, oic, cursor, settings, False)
                    _id = self.from_idol(_dumy, idol, True, id, oic, cursor, settings)
                    if idol.b_cloud: self.from_geometryset(idol.cloud, idol.refs, idol.name, _dumy, _id, depsgraph, oic, cursor, settings)
    

    def resolve_idol(self, context, b_particle, depsgraph, oic, cursor, settings, b_add = False):
        # self.resolve_idol(_asset, False, oic, cursor, settings, True)
        #TODO problem if context.data is for some a particle and others a mesh
        #TODO empties or other none data objects not yet supported
        _b_particle = b_particle and not settings.use_mesh_assets
        idol = cursor.idols.get(_vact_hash(context.data, _b_particle))
        if not idol:
            name = context.data.name
            _object = context
            if not b_add:
                _object = context.copy()
                _object.data = context.data
                _object.animation_data_clear()
                for mod in _object.modifiers[:]: _object.modifiers.remove(mod)
                _object.parent = None
                _object.matrix_world = mathutils.Matrix.Identity(4)
                cursor.into_assets.objects.link(_object)
            
            idol = VActIdol()
            idol.asset, idol.type, idol.name, idol.entry, idol.decomp = cursor.hlpr.asset(name, _b_particle, settings.module_name, settings.asset_path)
            idol.name = name = idol.name or name
            idol.object = _object

            idol.oic = VActOIC.Object()
            idol.oic.type = idol.type
            idol.oic.asset = idol.asset

            idol.eval_obj = depsgraph.id_eval_get(context)
            if idol.eval_obj is not context: idol.eval_geom = idol.eval_obj.evaluated_geometry()
            
            if idol.eval_geom:
                # maybe move up, need to be referenced in RulesSet
                idol.b_jump = context.name.startswith('GX_')#idol.decomp[3] in {'GX_'}
                idol.cloud = idol.eval_geom.instances_pointcloud()
                idol.refs = idol.eval_geom.instance_references()
                idol.b_cloud = idol.cloud and idol.refs
                #if idol.b_cloud: self.from_geometryset(context, idol.cloud, idol.refs, idol.name, _dumy, -1, depsgraph, oic, cursor, settings)                  

            _meta = self.resolve_meta(idol.object.data, cursor, settings)
            if (_meta): idol.oic.meta = oic.add_meta(_meta)

            idol.b_ignore = (settings.use_ignore_invalid and not idol.asset)
            b_add = (not idol.b_jump) and (not idol.b_ignore)
            if (b_add): oic.add_object(idol.oic)
            else: print(('-ignore','idol.name',idol.name))
            
            cursor.idols[_vact_hash(_object.data, _b_particle)] = idol
            cursor.exclude.add(_object)
        return idol
    
    def to_lod_group(self, context, name, lods, settings):
        into = "_LOD_GROUPS"
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
            
    def to_link(self, context, cursor, settings):
        base_directory = os.path.dirname(bpy.data.filepath)
        print(("file", base_directory))
        link = self.resolve_link(context, cursor, settings)
        _directory = os.path.dirname(os.path.relpath(link.file))
        _filepath = os.path.join(base_directory,_directory, link.file) 
        
        os.makedirs(os.path.join(base_directory,_directory), exist_ok=True)
        
        print((context.name, base_directory,_directory, link.file, _filepath))
        
        context.object.select_set(True)
        b_valid = _filepath and base_directory

        if b_valid:
            self._export_as(_filepath, base_directory, settings)
        context.object.select_set(False)

    def from_depsgraph(self, context, oic, cursor, settings):
        depsgraph = context.evaluated_depsgraph_get()
        if settings.use_ignore_particle_system:
            _dumy = _VActDummyInstance()
            b_particle = False
            for object in bpy.context.selected_objects:
                b_skip = not object.data or (object in cursor.exclude)
                if b_skip: continue
                idol = self.resolve_idol(object, b_particle, depsgraph, oic, cursor, settings)
                b_ignore = idol.b_ignore
                if b_ignore: continue
                _dumy.object = object
                _dumy.matrix_world = object.matrix_world
                _id = self.from_idol(_dumy, idol, b_particle, -1, oic, cursor, settings)
                if idol.b_cloud: self.from_geometryset(idol.cloud, idol.refs, idol.name, _dumy, _id, depsgraph, oic, cursor, settings)
        else:
            for instance in depsgraph.object_instances:
                _object = instance.instance_object or instance.object
                b_skip = (not _object.data
                            or not (instance.show_self
                                    and ( _object.original.select_get() 
                                        or (instance.is_instance 
                                            and _object.parent 
                                            and _object.parent.original.select_get())))
                            or (_object in cursor.exclude))
                if b_skip: continue
                b_particle = bool(instance.parent) or instance.is_instance
                idol = self.resolve_idol(_object.original, b_particle, depsgraph, oic, cursor, settings)
                b_ignore = (((not instance.particle_system) and idol.b_cloud and instance.is_instance) or idol.b_ignore)
                if b_ignore: continue
                # TODO resolve parent id in desgraph context
                _id = self.from_idol(instance, idol, b_particle, -1, oic, cursor, settings)
                if idol.b_cloud: self.from_geometryset(idol.cloud, idol.refs, idol.name, instance, _id, depsgraph, oic, cursor, settings)
        
    def from_idol(self, context, idol, b_particle, parent, oic, cursor, settings):        
        _instance = VActOIC.Instance()
        _instance.parent = parent
        _instance.object = idol.oic.id
        _instance.transform = self._to_transform(context, cursor, settings)
        _meta = self.resolve_meta(context.object, cursor, settings) if b_particle else None
        if not idol.b_jump:
            if (_meta): _instance.meta = oic.add_meta(_meta)
            oic.add_instance(_instance)
        return _instance.id
    
    def from_root(self, context, oic, cursor, settings):
        oic.axis = settings.vact_axis
        if settings.use_clear_assets:
            for _asset in cursor.into_assets.objects: bpy.data.objects.remove(_asset)
        else:
            for _asset in cursor.into_assets.objects: self.resolve_idol(_asset, False, None, oic, cursor, settings, True)
        self.from_depsgraph(context, oic, cursor, settings)
        return oic
    
    def do_export_normal(self, context, filepath):
        with open(filepath, "w", encoding='utf-8') as file:
            file.write(context.json())
            file.close()
    
    def do_export_compact(self, context, filepath):
        with open(filepath+"c", "w", encoding='utf-8') as file:
            file.write(context.compact())
            file.close()
            
    def do_export_binary(self, context, filepath):
        with open(filepath+"b", "wb") as file:
            file.write(context.binary())
            file.close()
    
    def _resolve_axis(self, cursor, settings):
        settings._up = 'Z'
        settings._forward = '-Y'
        if settings.vact_axis in {'UnrealEngine'}:
            # RH Zu nYf -> LH Zu Xf
            settings._up = 'Z'
            settings._forward = 'X'
            # cursor.axis = mathutils.Matrix((
            #     (0, -1, 0,  0),  # Swap X and Y
            #     (1,  0, 0,  0),  # Swap X and Y
            #     (0,  0, 1,  0),  # Keep Z as is
            #     (0,  0, 0,  1),  # No change to translation
            # ))
        elif settings.vact_axis in {'TreeJS'}:
            # RH Zu nYf -> RH Yu Zf
            settings._up = 'Y'
            settings._forward = 'Z'
        elif settings.vact_axis in {'BabylonJs', 'Unity'}:
            # RH Zu nYf -> LH Yu Zf
            #settings._up = 'Y'
            #settings._forward = 'Z'
            cursor.axis = mathutils.Matrix((
                (1,  0, 0,  0),  # Keep X as is
                (0,  0, 1,  0),  # Swap Y and Z
                (0, -1, 0,  0),  # Swap Y and Z
                (0,  0, 0, -1),  # No change to translation
            ))
        elif settings.vact_axis in {'Blender'}:
            settings._up = 'Z'
            settings._forward = '-Y'
        

    def do_export(self, context, filepath, settings):       
        layer = bpy.context.view_layer
        active = layer.objects.active
        selections = bpy.context.selected_objects        
        
        cursor = _VAct_OICCursor()
        self._resolve_axis(cursor, settings)
        cursor.hlpr = _vact_resolve_hlpr(settings.vact_axis,{}) 
        # VActCheckAny([
        #     VActCheckContains("Buildings/Proxy/", "Proxy"),
        #     VActCheckContains("Buildings/Decor/", "Decor"),
        #     VActCheckContains("Buildings/Backwall/", "Backwall"),
        #     VActCheckContains("Buildings/Fill/", "Fill"),
        #     VActCheckContains("Buildings/Foundation/", "Foundation"),
        #     VActCheckContains("Buildings/Glass/", "Glass"),
        #     VActCheckContains("Buildings/Overhang/", "Overhang"),
        #     VActCheckContains("Buildings/Roof/", "Roof"),
        #     VActCheckContains("Buildings/Base/", "Building")
        # ])
        
        cursor.into_assets = bpy.data.collections[settings.root]

        oic = self.from_root(bpy.context, VActOIC(settings.object_name), cursor, settings)
        
        if settings.oic_format in {'JSON'}:
            self.do_export_normal(oic, filepath)
        elif settings.oic_format in {'PACK'}:
            self.do_export_compact(oic, filepath)
        elif settings.oic_format in {'BIN'}:
            self.do_export_binary(oic, filepath)
        else: raise Exception("Invalid OIC format selected")
        
        if settings.use_export_objects:
            bpy.ops.object.select_all(action='DESELECT')
            for idol in cursor.idols.values():
                # TODO if there is a particle and mesh of the same object, a double export may happen
                #print(("-idol",idol.name, idol.b_jump, idol.type))
                b_export = (not idol.b_jump) and idol.type in {'Mesh', 'Particle'}
                if b_export: self.to_link(idol, cursor, settings)

        print([('len(oic.objects)',len(oic.objects)),('len(oic.instances)',len(oic.instances)),('len(oic.metas)',len(oic.metas))])
        
        return {'FINISHED'}
    
    def do_import(self, context, filepath, settings):
        # with open(filepath, 'r', encoding='utf-8') as file:
        #     oic = json.load(file, cls=_VAct_OICEncoder)
        #     file.close()
        
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
    use_mesh_assets : BoolProperty(name="Particles To Mesh", default=False)
    use_ignore_particle_system : BoolProperty(name="Ignore Particle Systems", default=False)
    use_export_animation : BoolProperty(name="Export Animations", default=False)
    use_export_selected_objects : BoolProperty(name="Export Selected", default=False)
    use_export_objects : BoolProperty(name="Export Objects", default=False, description = "Export the objects, not only composition info")
    use_overwrite_existing : BoolProperty(name="Overwrite Existing", default=True)
    use_ignore_invalid : BoolProperty(name="Ignore Invalid", default=True)
    use_clear_assets : BoolProperty(name="Clear Assets", default=False)
    scale_correct : FloatProperty(name="Scale Correct", default=1.0)
    
    @classmethod
    def register_menu(cls, self, context):
        self.layout.operator(cls.bl_idname, text=cls.bl_label)


class VActExportOICSettings(VActFormatOICHelper):
    bl_menu = "TOPBAR_MT_file_export"

    root : StringProperty(name="Root Collection", default="_Assets")
    #root : PointerProperty(name="Root Collection", type=bpy.types.Collection)
    asset_path : StringProperty(name="Asset Path", default='')
    module_name : StringProperty(name="Module", default='Engine')
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
    
    vact_axis : EnumProperty(
        name="Axis System",
        description="Select Your Axis System",
        items=(
            ('Unity', "Unity", "As Unity Axis"),
            ('Blender', "Blender", "As Blender Axis"),
            ('TreeJS', "TreeJS", "As TreeJS Axis"),
            ('UnrealEngine', "Unreal Engine", "As Unreal Engine Axis"),
            ('BabylonJs', "BabylonJs", "As BabylonJs Axis"),
        ),
        default='UnrealEngine'
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
    vact_type : StringProperty(name="Type", default= "", options={'HIDDEN', 'LIBRARY_EDITABLE'})
    vact_name : StringProperty(name="Name", default="_Nameless", options={'LIBRARY_EDITABLE'})
    vact_enabled : BoolProperty(name="Enabled", default=True, options={'LIBRARY_EDITABLE'})

    vact_Name : StringProperty(name="Name", default="_Value", options={'HIDDEN', 'LIBRARY_EDITABLE'})
    vact_String : StringProperty(name="String", default="_Value", options={'HIDDEN', 'LIBRARY_EDITABLE'})
    vact_Bool : BoolProperty(name="Bool", default=True, options={'HIDDEN', 'LIBRARY_EDITABLE'})
    vact_Int : IntProperty(name="Int", default=0, options={'HIDDEN', 'LIBRARY_EDITABLE'})
    vact_Float : FloatProperty(name="Float", default=0.0, options={'HIDDEN', 'LIBRARY_EDITABLE'})
    #vact_Asset : PointerProperty(name="Asset", type=VActAsset)

    ##vact_Int2 : IntProperty(name="Int2", default=(0,0), options={'HIDDEN', 'LIBRARY_EDITABLE'}, size = 2)
    #vact_Float2 : FloatProperty(name="Float2", default=(0.0,0.0), options={'HIDDEN', 'LIBRARY_EDITABLE'}, size = 2)
    ##vact_Int3 : IntProperty(name="Int3", default=(0,0,0), options={'HIDDEN', 'LIBRARY_EDITABLE'}, size = 3)
    #vact_Float3 : FloatProperty(name="Float3", default=(0.0,0.0,0.0), options={'HIDDEN', 'LIBRARY_EDITABLE'}, size = 3)
    ##vact_Int4 : IntProperty(name="Int4", default=(0,0,0,0), options={'HIDDEN', 'LIBRARY_EDITABLE'}, size = 4)
    #vact_Float4 : FloatProperty(name="Float4", default=(0.0,0.0,0.0,0.0), options={'HIDDEN', 'LIBRARY_EDITABLE'}, size = 4)
    ##vact_Int5 : IntProperty(name="Int5", default=(0,0,0,0,0), options={'HIDDEN', 'LIBRARY_EDITABLE'}, size = 5)
    #vact_Float5 : FloatProperty(name="Float5", default=(0.0,0.0,0.0,0.0,0.0), options={'HIDDEN', 'LIBRARY_EDITABLE'}, size = 5)
    ##vact_Int6 : IntProperty(name="Int6", default=(0,0,0,0,0,0), options={'HIDDEN', 'LIBRARY_EDITABLE'}, size = 6)
    #vact_Float6 : FloatProperty(name="Float6", default=(0.0,0.0,0.0,0.0,0.0,0.0), options={'HIDDEN', 'LIBRARY_EDITABLE'}, size = 6)

    ##vact_Ints : CollectionProperty(name="Ints", type=VActInt)
    ##vact_Floats : CollectionProperty(name="Floats", type=VActFloat)
    ##vact_Names : CollectionProperty(name="Names", type=VActString)
    ##vact_Strings : CollectionProperty(name="Strings", type=VActString)
    ##vact_Assets : CollectionProperty(name="Strings", type=VActAsset)

class VActMetaEntry(PropertyGroup):
    vact_asset : StringProperty(name="Asset", default="_Nameless", options={'LIBRARY_EDITABLE'})
    vact_enabled : BoolProperty(name="Enabled", default=True, options={'LIBRARY_EDITABLE'})
    vact_properties: CollectionProperty(name="Meta Data", type=VActProperty)
    vact_properties_index : IntProperty(name="Meta Index", default=0, min=0)
    
    bpy.types.Object,
    bpy.types.Curves,
    bpy.types.Light,
    bpy.types.Mesh,
    bpy.types.Camera,
    bpy.types.Sound,
    bpy.types.Speaker,
    bpy.types.Armature,
    bpy.types.Curve

class VActMeta:
    @classmethod
    def meta(cls, context=None):
        return context.mesh or context.curve or context.light or context.camera or context.speaker or context.armature or context.curves or context.object or context
    
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
    
    @classmethod
    def property(cls, context=None):
        entry = cls.entry(context)
        return entry.vact_properties[entry.vact_properties_index]
    
    @classmethod
    def property_add(cls, context=None):
        entry = cls.entry(context)
        return entry.vact_properties.add()
    
    @classmethod
    def property_remove(cls, context=None, target=None):
        entry = cls.entry(context)
        entry.vact_properties.remove(entry.vact_properties_index)
        entry.vact_properties_index -= 1

    @classmethod
    def property_poll(cls, context=None):
        if cls.entry_poll(context):
            entry = cls.entry(context)
            return bool(entry) and bool(entry.vact_properties) and entry.vact_properties_index < len(entry.vact_properties)
        return False
    
    @classmethod
    def property_selected(cls, index, context):
        entry = cls.entry(context)
        return index == entry.vact_properties_index


class VActPropertyHelper(VActHelper):
    bl_menu = None

class VActEntryHelper(VActHelper):
    bl_menu = None

class VACTPROPERTY_OT_Delete(Operator, VActPropertyHelper):
    """Delete Property"""
    bl_idname = "vact.delete_property"
    bl_label = "Delete"

    def execute(self, context):
        VActMeta.property_remove(context)
        return {'FINISHED'}


class VACTPROPERTY_OT_String_New(Operator, VActPropertyHelper):
    """Create String Property"""
    bl_idname = "vact.new_property_string"
    bl_label = "String"
    bl_icon = 'EVENT_S'

    def execute(self, context):
        property = VActMeta.property_add(context)
        property.vact_name = "MyString"
        property.vact_type = "String"
        property.vact_icon = self.bl_icon
        return {'FINISHED'}

class VACTPROPERTY_OT_Int_New(Operator, VActPropertyHelper):
    """Create Int Property"""
    bl_idname = "vact.new_property_int"
    bl_label = "Int"
    bl_icon = 'EVENT_I'

    def execute(self, context):
        property = VActMeta.property_add(context)
        property.vact_name = "MyInt"
        property.vact_type = "Int"
        property.vact_icon = self.bl_icon
        return {'FINISHED'}

class VACTPROPERTY_OT_Float_New(Operator, VActPropertyHelper):
    """Create Float Property"""
    bl_idname = "vact.new_property_float"
    bl_label = "Float"
    bl_icon = 'EVENT_F'

    def execute(self, context):
        property = VActMeta.property_add(context)
        property.vact_name = "MyFloat"
        property.vact_type = "Float"
        property.vact_icon = self.bl_icon
        return {'FINISHED'}

class VACTPROPERTY_OT_Bool_New(Operator, VActPropertyHelper):
    """Create Bool Property"""
    bl_idname = "vact.new_property_bool"
    bl_label = "Bool"
    bl_icon = 'EVENT_B'

    def execute(self, context):
        property = VActMeta.property_add(context)
        property.vact_name = "MyBool"
        property.vact_type = "Bool"
        property.vact_icon = self.bl_icon
        return {'FINISHED'}
    
class VACTPROPERTY_OT_Name_New(Operator, VActPropertyHelper):
    """Create Name Property"""
    bl_idname = "vact.new_property_name"
    bl_label = "Name"
    bl_icon = 'EVENT_N'

    def execute(self, context):
        property = VActMeta.property_add(context)
        property.vact_name = "MyName"
        property.vact_type = "Name"
        property.vact_icon = self.bl_icon
        return {'FINISHED'}
    

class VACTENTRY_OT_Delete(Operator, VActPropertyHelper):
    """Delete Entry"""
    bl_idname = "vact.delete_entry"
    bl_label = "Delete"

    def execute(self, context):
        VActMeta.entry_remove(context)
        return {'FINISHED'}
    
class VACTENTRY_OT_New(Operator, VActPropertyHelper):
    """New Entry"""
    bl_idname = "vact.new_entry"
    bl_label = "New"

    def execute(self, context):
        entry = VActMeta.entry_add(context)
        return {'FINISHED'}

class VACTENTRY_UL_List(UIList):
    """Entry List"""
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            b_selected = VActMeta.entry_selected(index, context)
            _val_emboss = 'NORMAL' if b_selected else 'NONE' 
            _val_x = 16
            row = layout.row()
            sub = row.row(align=True)
            sub.prop(item, 'vact_asset', text="", emboss=b_selected)
            val = sub.row(align=True)
            #val.prop(item, item, text=item.vact_asset, emboss=b_selected)
            val.ui_units_x = _val_x
            val.emboss = _val_emboss
            #sub.alignment = _val_align
            sub.enabled = item.vact_enabled
            row.prop(item, 'vact_enabled', text="")
            row.enabled = b_selected

        if self.layout_type in {'GRID'} :
            layout.alignment = 'CENTER'
            layout.label(text=item.vact_asset)

class VACTPROPERTY_UL_List(UIList):
    """Property List"""
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        _icon = icon if item.vact_icon is None else item.vact_icon
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            b_val_bool = item.vact_type in {'Bool'}
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
        layout.operator("vact.new_property_name", icon='EVENT_N')
        #layout.operator("vact.new_property_asset", icon='EVENT_A')
        ##layout.operator("vact.new_property_int2", icon='EVENT_I2')
        #layout.operator("vact.new_property_float2", icon='EVENT_F2')
        ##layout.operator("vact.new_property_int3", icon='EVENT_I3')
        #layout.operator("vact.new_property_float3", icon='EVENT_F3')
        ##layout.operator("vact.new_property_int4", icon='EVENT_I4')
        #layout.operator("vact.new_property_float4", icon='EVENT_F4')
        ##layout.operator("vact.new_property_int5", icon='EVENT_I5')
        #layout.operator("vact.new_property_float5", icon='EVENT_F5')
        ##layout.operator("vact.new_property_int6", icon='EVENT_I6')
        #layout.operator("vact.new_property_float6", icon='EVENT_F6')
        ##layout.operator("vact.new_property_ints", icon='EVENT_I')
        ##layout.operator("vact.new_property_floats", icon='EVENT_F')
        ##layout.operator("vact.new_property_strings", icon='EVENT_S')
        ##layout.operator("vact.new_property_names", icon='EVENT_N')
        ##layout.operator("vact.new_property_assets", icon='EVENT_A')


class VACTMETA_PT_Main:
    """Meta Data Control Panel"""
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_options = {"DEFAULT_CLOSED"}

    bl_label = "Meta Data"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        meta = VActMeta.meta(context)

        row = layout.row()
        row.template_list('VACTENTRY_UL_List', "", meta, "vact_meta", meta, "vact_meta_index")
        col = row.column(align=True)
        col.operator("vact.new_entry", icon='ADD', text="")
        col.operator("vact.delete_entry", icon='REMOVE', text="")
        layout.separator()

        if VActMeta.entry_poll(context) and False:
            entry = VActMeta.entry(context)
            row = layout.row()
            col = row.column()
            col.template_list('VACTPROPERTY_UL_List', "", entry, "vact_properties", entry, "vact_properties_index")
            col = row.column(align=True)
            col.menu('VACTPROPERTY_MT_Add_Property', text='', icon='ADD')
            col.operator("vact.delete_property", text="", icon='REMOVE')
            layout.separator()

            if VActMeta.property_poll(context):
                property = VActMeta.property(context)
                b_val_bool = property.vact_type in {'Bool'}
                _val_text = str(property.vact_b) if b_val_bool else ""
                _val_align = 'CENTER' if b_val_bool else 'EXPAND'

                row = layout.row(align=True)
                col = row.column(align=True)
                col.prop(property,"vact_name")
                row = layout.row()
                row.prop(property, property.vact_ctx, text=_val_text)
                row.alignment = _val_align
                
                row.enabled = col.enabled = property.vact_enabled


class VACTMETA_PT_Object(VACTMETA_PT_Main, Panel):
    bl_idname = "VACTMETA_PT_Object"
    bl_context = "object"

class VACTMETA_PT_Data(VACTMETA_PT_Main, Panel):
    bl_idname = "VACTMETA_PT_Data"
    bl_context = "data"

supported_metas = (
    bpy.types.Object,
    bpy.types.Curves,
    bpy.types.Light,
    bpy.types.Mesh,
    bpy.types.Camera,
    bpy.types.Sound,
    bpy.types.Speaker,
    bpy.types.Armature,
    bpy.types.Curve
)

operators = (
    ImportOIC,
    ExportOIC,
    VACTPROPERTY_OT_Delete,
    VACTPROPERTY_OT_String_New,
    VACTPROPERTY_OT_Int_New,
    VACTPROPERTY_OT_Float_New,
    VACTPROPERTY_OT_Bool_New,
    VACTPROPERTY_OT_Name_New,
    VACTENTRY_OT_Delete,
    VACTENTRY_OT_New
)

classes = (
    VActHelper,
    VActPropertyHelper,
    VActProperty,
    VActEntryHelper,
    VActMetaEntry,
    VActFormatOICHelper,
    VActImportOICSettings,
    VActExportOICSettings,
    VACTPROPERTY_UL_List,
    VACTPROPERTY_MT_Add_Property,
    VACTENTRY_UL_List,
    VACTMETA_PT_Object,
    VACTMETA_PT_Data
) + operators

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
        
    for ops in operators:
        if ops.bl_menu:
            getattr(bpy.types,ops.bl_menu).append(ops.register_menu)
    
    for spm in supported_metas:
        spm.vact_meta = CollectionProperty(name="Meta Data", type=VActMetaEntry)
        spm.vact_meta_index = IntProperty(name="Meta Index", default=0, min=0)

def unregister():
    for ops in operators:
        if ops.bl_menu:
            getattr(bpy.types,ops.bl_menu).remove(ops.register_menu)
        
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    for spm in supported_metas:
        del spm.vact_meta


if __name__ == "__main__":
    register()