bl_info = {
  "name": "MMD-AutoFace",
  "author": "Lq35_noitamina",
  "version": (1, 6),
  "blender": (3, 0, 0),
  "location": "View3D > Sidebar > MMD-AutoFace",
  "description": "テキストからの口パク生成と自動瞬きツールです。",
  "category": "Object",
}

import bpy
import random

VOWEL_MAP = {
  'あ': 'A', 'か': 'A', 'さ': 'A', 'た': 'A', 'な': 'A', 'は': 'A', 'ま': 'A', 'や': 'A', 'ら': 'A', 'わ': 'A',
  'が': 'A', 'ざ': 'A', 'だ': 'A', 'ば': 'A', 'ぱ': 'A', 'ぁ': 'A', 'ゃ': 'A',
  'い': 'I', 'き': 'I', 'し': 'I', 'ち': 'I', 'に': 'I', 'ひ': 'I', 'み': 'I', 'り': 'I',
  'ぎ': 'I', 'じ': 'I', 'ぢ': 'I', 'び': 'I', 'ぴ': 'I', 'ぃ': 'I',
  'う': 'U', 'く': 'U', 'す': 'U', 'つ': 'U', 'ぬ': 'U', 'ふ': 'U', 'む': 'U', 'ゆ': 'U', 'る': 'U',
  'ぐ': 'U', 'ず': 'U', 'づ': 'U', 'ぶ': 'U', 'ぷ': 'U', 'ぅ': 'U', 'ゅ': 'U',
  'え': 'E', 'け': 'E', 'せ': 'E', 'て': 'E', 'ね': 'E', 'へ': 'E', 'め': 'E', 'れ': 'E',
  'げ': 'E', 'ぜ': 'E', 'で': 'E', 'べ': 'E', 'ぺ': 'E', 'ぇ': 'E',
  'お': 'O', 'こ': 'O', 'そ': 'O', 'と': 'O', 'の': 'O', 'ほ': 'O', 'も': 'O', 'よ': 'O', 'ろ': 'O', 'を': 'O',
  'ご': 'O', 'ぞ': 'O', 'ど': 'O', 'ぼ': 'O', 'ぽ': 'O', 'ぉ': 'O', 'ょ': 'O',
  'ん': 'N',
}

TRANSITION_SCALE = {
  frozenset({'U', 'O'}): 0,
  frozenset({'I', 'E'}): 0,
  frozenset({'O', 'E'}): 1,
  frozenset({'A', 'O'}): 1,
  frozenset({'A', 'E'}): 1,
  frozenset({'A', 'I'}): 2,
  frozenset({'A', 'U'}): 2,
  frozenset({'I', 'U'}): 2,
}

CLOSE_MID_SCALE = {0: 0.8, 1: 0.4, 2: 0.0}

class MESH_OT_generate_lip_sync_text(bpy.types.Operator):
  bl_idname = "mesh.generate_lip_sync_text"
  bl_label = "テキストから口パク生成"
  bl_options = {'REGISTER', 'UNDO'}

  def execute(self, context):
    obj = context.active_object
    if not obj or not obj.data.shape_keys:
      self.report({'ERROR'}, "シェイプキーが見つかりません")
      return {'CANCELLED'}

    keys = obj.data.shape_keys.key_blocks
    scene = context.scene
    prefix = "G" if scene.mode_g else ""
    name_map = {k: prefix + getattr(scene, f"name_{k.lower()}") for k in 'AIUEO'}

    if scene.mode_g:
      for key_n, val in [("G上歯開", 0.30), ("G下歯開", 0.25)]:
        if key_n in keys:
          keys[key_n].value = val
          keys[key_n].keyframe_insert(data_path='value', frame=scene.lip_sync_start)

    all_target_names = list(name_map.values())
    script = scene.lip_sync_script
    cf = scene.lip_sync_start
    step = scene.lip_sync_step

    vowel_list = [VOWEL_MAP.get(char) for char in script]

    for i, char in enumerate(script):
      vowel_type = vowel_list[i]
      prev_vowel = vowel_list[i - 1] if i > 0 else None
      next_vowel = vowel_list[i + 1] if i < len(vowel_list) - 1 else None

      if vowel_type != prev_vowel or vowel_type == 'N':
        for kname in all_target_names:
          if kname in keys:
            keys[kname].value = 0.0
            keys[kname].keyframe_insert(data_path='value', frame=cf)

        if vowel_type and vowel_type != 'N':
          real_key_name = name_map[vowel_type]
          if real_key_name in keys:
            keys[real_key_name].value = scene.lip_sync_size
            keys[real_key_name].keyframe_insert(data_path='value', frame=cf)

      if scene.mode_close_mid and vowel_type and vowel_type != 'N':
        mid_f = cf + round(step / 2)
        pair = frozenset({vowel_type, next_vowel}) if next_vowel and next_vowel != 'N' else None
        scale = TRANSITION_SCALE.get(pair, 2) if pair else 2
        close_val = scene.lip_sync_close_value + (scene.lip_sync_size - scene.lip_sync_close_value) * CLOSE_MID_SCALE[scale]

        for kname in all_target_names:
          if kname in keys:
            keys[kname].value = close_val if kname == name_map.get(vowel_type) else 0.0
            keys[kname].keyframe_insert(data_path='value', frame=mid_f)

      cf += step

    return {'FINISHED'}

class MESH_OT_generate_blinks_auto(bpy.types.Operator):
  bl_idname = "mesh.generate_blinks_auto"
  bl_label = "瞬きを自動挿入"
  bl_options = {'REGISTER', 'UNDO'}

  def execute(self, context):
    obj = context.active_object
    key_name = context.scene.blink_key_name
    if key_name not in obj.data.shape_keys.key_blocks:
      self.report({'ERROR'}, f"キー「{key_name}」が見つかりません")
      return {'CANCELLED'}

    key = obj.data.shape_keys.key_blocks[key_name]
    cf = context.scene.blink_start
    end_f = context.scene.blink_end

    while cf < end_f:
      key.value = 0.0
      key.keyframe_insert(data_path='value', frame=cf)
      key.value = 1.0
      key.keyframe_insert(data_path='value', frame=cf + 2)
      key.value = 0.0
      key.keyframe_insert(data_path='value', frame=cf + 5)
      cf += random.randint(context.scene.lip_sync_min, context.scene.lip_sync_max)
    return {'FINISHED'}

class VIEW3D_PT_character_anim_panel(bpy.types.Panel):
  bl_space_type = 'VIEW_3D'
  bl_region_type = 'UI'
  bl_category = 'MMD-AutoFace'
  bl_label = 'MMD-AutoFace'

  def draw(self, context):
    layout = self.layout
    scene = context.scene

    box = layout.box()
    box.label(text="シェイプキー設定", icon='MODIFIER')
    for label, prop in [("あ", "name_a"), ("い", "name_i"), ("う", "name_u"), ("え", "name_e"), ("お", "name_o")]:
      row = box.row(align=True)
      split = row.split(factor=0.8)
      split.prop(scene, prop, text=label)
    box.prop(scene, "blink_key_name", text="まばたき")

    box = layout.box()
    box.label(text="動作設定", icon='PROPERTIES')
    row = box.row(align=True)
    row.prop(scene, "mode_g", text="Gモード", toggle=True)
    row.prop(scene, "mode_close_mid", text="合間閉", toggle=True)

    box = layout.box()
    box.label(text="口パク実行", icon='COMMUNITY')
    box.prop(scene, "lip_sync_script")
    col = box.column(align=True)
    col.prop(scene, "lip_sync_size", text="開き具合")
    col.prop(scene, "lip_sync_close_value", text="合間の閉じ感")

    row = box.row(align=True)
    row.prop(scene, "lip_sync_start", text="開始")
    row.prop(scene, "lip_sync_step", text="間隔")
    box.operator("mesh.generate_lip_sync_text", icon='PLAY')

    box = layout.box()
    box.label(text="瞬き実行", icon='HIDE_OFF')
    row = box.row(align=True)
    row.prop(scene, "blink_start", text="開始")
    row.prop(scene, "blink_end", text="終了")
    col = box.column(align=True)
    col.prop(scene, "lip_sync_min", text="最小間隔")
    col.prop(scene, "lip_sync_max", text="最大間隔")
    box.operator("mesh.generate_blinks_auto", icon='PLAY')

classes = (MESH_OT_generate_lip_sync_text, MESH_OT_generate_blinks_auto, VIEW3D_PT_character_anim_panel)

def register():
  for cls in classes:
    bpy.utils.register_class(cls)

  s = bpy.types.Scene
  s.name_a = bpy.props.StringProperty(name="あ", default="あ")
  s.name_i = bpy.props.StringProperty(name="い", default="い")
  s.name_u = bpy.props.StringProperty(name="う", default="う")
  s.name_e = bpy.props.StringProperty(name="え", default="え")
  s.name_o = bpy.props.StringProperty(name="お", default="お")
  s.mode_g = bpy.props.BoolProperty(name="Gモード", default=False)
  s.mode_close_mid = bpy.props.BoolProperty(name="合間に閉じる", default=False)
  s.blink_key_name = bpy.props.StringProperty(name="瞬き", default="まばたき")
  s.lip_sync_script = bpy.props.StringProperty(name="台本", default="こんにちは")
  s.lip_sync_size = bpy.props.FloatProperty(name="開き", default=0.75, min=0.0, max=1.0)
  s.lip_sync_close_value = bpy.props.FloatProperty(name="閉じ", default=0.0, min=0.0, max=1.0)
  s.lip_sync_start = bpy.props.IntProperty(name="開始", default=1)
  s.lip_sync_step = bpy.props.IntProperty(name="間隔", default=6)
  s.blink_start = bpy.props.IntProperty(name="開始", default=1)
  s.blink_end = bpy.props.IntProperty(name="終了", default=250)
  s.lip_sync_min = bpy.props.IntProperty(name="最小", default=20)
  s.lip_sync_max = bpy.props.IntProperty(name="最大", default=160)

def unregister():
  for cls in reversed(classes):
    bpy.utils.unregister_class(cls)

  s = bpy.types.Scene
  del s.name_a, s.name_i, s.name_u, s.name_e, s.name_o
  del s.mode_g, s.mode_close_mid, s.blink_key_name
  del s.lip_sync_script, s.lip_sync_size, s.lip_sync_close_value
  del s.lip_sync_start, s.lip_sync_step
  del s.blink_start, s.blink_end, s.lip_sync_min, s.lip_sync_max

if __name__ == "__main__":
  register()
