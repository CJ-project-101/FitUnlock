import QtQuick

Item {
    id: bd
    property real intensity: 1.0          // 0 = invisible, 1 = default. Lower it for an even subtler look
    property real t: 0
    readonly property bool animate: visible && Qt.application.state === Qt.ApplicationActive

    NumberAnimation on t { from: 0; to: 1; duration: 4600; loops: Animation.Infinite; running: bd.animate }

    // timeline: 0 -> flight = left to right, then a short hold, then right to left, then a short hold
    readonly property real flight: 0.3696
    readonly property real hold: 0.1304

    // layout
    readonly property real sc: Math.max(0.55, Math.min(1.25, height / 760))
    readonly property real leftX: width * 0.13
    readonly property real rightX: width * 0.87
    readonly property real groundY: height - 30 * sc
    readonly property real holdY: groundY - 121 * sc
    readonly property real hxL: leftX + 26 * sc
    readonly property real hxR: rightX - 26 * sc
    readonly property real arc: Math.min(220, (hxR - hxL) * 0.28)

    // front-arm angle over one cycle: release at 0, follow through, rest, reach up to catch, cushion, wind up
    readonly property var armFrames: [[0, -140], [0.08, -35], [0.2, 0], [0.64, 0], [0.83, -115],
                                      [0.8696, -125], [0.905, -75], [0.965, 60], [1, -140]]

    function kf(t, frames) {
        for (var i = 1; i < frames.length; i++) {
            if (t <= frames[i][0]) {
                var a = frames[i - 1], b = frames[i]
                var u = (t - a[0]) / (b[0] - a[0])
                u = u * u * (3 - 2 * u)           // smooth in and out
                return a[1] + (b[1] - a[1]) * u
            }
        }
        return frames[frames.length - 1][1]
    }
    function ballX(t) {
        if (t < flight) return hxL + (hxR - hxL) * (t / flight)
        if (t < flight + hold) return hxR
        if (t < 2 * flight + hold) return hxR + (hxL - hxR) * ((t - flight - hold) / flight)
        return hxL
    }
    function ballY(t) {
        var u
        if (t < flight) u = t / flight
        else if (t >= flight + hold && t < 2 * flight + hold) u = (t - flight - hold) / flight
        else return holdY
        return holdY - arc * 4 * u * (1 - u)       // parabola
    }

    // ---- background ----
    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#0b0d1b" }
            GradientStop { position: 1.0; color: "#05060c" }
        }
    }
    // two slow colour washes for a little depth
    Rectangle {
        width: 620; height: 620; radius: 310
        color: "#7c5cff"; opacity: 0.05 * bd.intensity
        x: -160; y: bd.height * 0.35
        SequentialAnimation on x {
            loops: Animation.Infinite; running: bd.animate
            NumberAnimation { to: 40; duration: 11000; easing.type: Easing.InOutSine }
            NumberAnimation { to: -160; duration: 11000; easing.type: Easing.InOutSine }
        }
    }
    Rectangle {
        width: 520; height: 520; radius: 260
        color: "#0fd8a8"; opacity: 0.035 * bd.intensity
        x: bd.width - 380; y: bd.height * 0.05
        SequentialAnimation on scale {
            loops: Animation.Infinite; running: bd.animate
            NumberAnimation { to: 1.18; duration: 9000; easing.type: Easing.InOutSine }
            NumberAnimation { to: 1.0; duration: 9000; easing.type: Easing.InOutSine }
        }
    }

    // ---- the two figures ----
    Item {
        anchors.fill: parent
        opacity: 0.20 * bd.intensity

        Rectangle { x: bd.leftX - 44 * bd.sc;  y: bd.groundY + 3; width: 88 * bd.sc; height: 2; radius: 1; color: "#9aa5ff" }
        Rectangle { x: bd.rightX - 44 * bd.sc; y: bd.groundY + 3; width: 88 * bd.sc; height: 2; radius: 1; color: "#9aa5ff" }

        Stickman {
            x: bd.leftX; y: bd.groundY
            figureScale: bd.sc
            frontArm: bd.kf(bd.t, bd.armFrames)
            backArm: 10 + 7 * Math.sin(bd.t * 4 * Math.PI)
            bob: 2.5 * (1 + Math.sin(bd.t * 4 * Math.PI))
        }
        Stickman {
            mirror: true
            x: bd.rightX; y: bd.groundY
            figureScale: bd.sc
            frontArm: bd.kf((bd.t + 0.5) % 1, bd.armFrames)
            backArm: 10 + 7 * Math.sin((bd.t + 0.5) * 4 * Math.PI)
            bob: 2.5 * (1 + Math.sin((bd.t + 0.5) * 4 * Math.PI))
        }
    }

    // ---- the ball with a short fading trail ----
    Repeater {
        model: 3
        Rectangle {
            id: ghost
            required property int index
            readonly property real tt: (bd.t - (index + 1) * 0.011 + 1) % 1
            width: 14 * bd.sc * (1 - index * 0.18); height: width; radius: width / 2
            color: "#ffcf6b"
            opacity: (0.18 - index * 0.05) * bd.intensity
            x: bd.ballX(tt) - width / 2
            y: bd.ballY(tt) - height / 2
        }
    }
    Rectangle {
        width: 15 * bd.sc; height: width; radius: width / 2
        color: "#ffcf6b"
        opacity: 0.42 * bd.intensity
        x: bd.ballX(bd.t) - width / 2
        y: bd.ballY(bd.t) - height / 2
    }
}