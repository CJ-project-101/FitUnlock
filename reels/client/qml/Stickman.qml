import QtQuick

// A simple stick figure. Its origin (0,0) is the feet. Angles are in degrees (0 = arm hanging down).
Item {
    id: man
    property real frontArm: 0
    property real backArm: 8
    property real bob: 0
    property bool mirror: false
    property real figureScale: 1
    property color tint: "#9aa5ff"

    width: 0; height: 0
    scale: figureScale
    transformOrigin: Item.TopLeft
    transform: Scale { xScale: man.mirror ? -1 : 1; origin.x: 0; origin.y: 0 }

    // legs
    Rectangle { x: -2.5; y: -50; width: 5; height: 50; radius: 2.5; color: man.tint; transformOrigin: Item.Top; rotation: 7 }
    Rectangle { x: -2.5; y: -50; width: 5; height: 50; radius: 2.5; color: man.tint; transformOrigin: Item.Top; rotation: -7 }

    Item {
        y: -man.bob
        Rectangle { x: -3; y: -96; width: 6; height: 46; radius: 3; color: man.tint }          // torso
        Rectangle { x: -11; y: -124; width: 22; height: 22; radius: 11; color: man.tint }      // head
        Rectangle { x: -2.5; y: -90; width: 5; height: 40; radius: 2.5; color: man.tint
                    transformOrigin: Item.Top; rotation: man.backArm }
        Rectangle { x: -2.5; y: -90; width: 5; height: 40; radius: 2.5; color: man.tint
                    transformOrigin: Item.Top; rotation: man.frontArm }
    }
}