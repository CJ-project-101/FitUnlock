import QtQuick
import QtQuick.Controls

TextField {
    id: tf
    color: Theme.text
    placeholderTextColor: Theme.muted
    selectionColor: Theme.accent
    font.pixelSize: 14
    leftPadding: 14; rightPadding: 14; topPadding: 11; bottomPadding: 11
    background: Rectangle {
        radius: 10
        color: Theme.card
        border.width: 1
        border.color: tf.activeFocus ? Theme.accent : Theme.border
    }
}