# AdditiveAnimationModifiers
Blender Addon: Adds additive animation tracks to current pose.

Panel in: Properties -> Data -> Additive animation modifiers.

![screen](screen.png 'Addon location')

Option "Enable addon for scene" is necessary to calculate additive animation. Hovewer, addon forces all bones (even those unused in action) to be calculated every frame.

Installation

It is a plugin. Select "File -> User Preferences" and choose "Addon" tab. Click "Install from file..." and choose downloaded file.

Setting a shortcut

There is insert keyframe menu similar to this activated using 'I' key.

User preferences -> Input -> 3D View -> 3D View (Global).
Press "Add new".
Fill field with "anim.insert_keyframe_menu".

Limitation

- Only location and rotation.
- No Axis Angle rotation mode support now.
- Auto generating keyframes should be disabled.
- Every time scene frame changed, all bones (even those unused in action) will be calculated from rest pose (works like "Clear pose transforms" on all unused bones). To disable this behaviour disable "Enable addon for scene".
- Additive animation track will be used without constraints.
- Changing every property (like visibility of additive animation modifier) cause lost of modified pose transforms.
