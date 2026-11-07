# Visages4K / K_HEAD_V3 merged resource selection

This merge preserves K_HEAD_V3's12morph-target resources, pale-skin material instance and unique-eye texture; Visages supplies all10face texture resources. Six conflicting paths are resolved to Visages. The two differently prefixed Visages input archives are byte-identical priority copies.

Every selected resource is copied unchanged, then packed and reextracted using official WolvenKit8.18.0 ConsoleLinux. The24reextracted resources match their selected original bytes. The merged archive's path/hash inventory equals the input union. `selected-resources.json` maps each resource to its chosen source and SHA256; `resource-conflicts.json` lists all six differing overlaps.

The base K_HEAD morph references the shared n01 normal. The K_HEAD normal is1024² with11mips; Visages is4096² with1mip. Both declare TCM_Normalmap. The base morph render header declares numTargets0, and all6 texture-diff descriptor arrays are empty. Original morph bytes, including raw buffers, are retained. No texture resizing, recompression of internal resources, or morph-buffer rebasing is performed.

This selects K_HEAD head morphology plus Visages texture style. K_HEAD's original diffuse pixels and base-normal shading are replaced at the6shared paths. Its unique pale-skin material values are retained. Actual game appearance, lighting and gameplay compatibility have not been tested here. See the report and Korean install instructions beside the downloadable archive.
