pragma Singleton
import QtQuick

QtObject {
    readonly property string reels: "M5 3 H19 A2 2 0 0 1 21 5 V19 A2 2 0 0 1 19 21 H5 A2 2 0 0 1 3 19 V5 A2 2 0 0 1 5 3 Z M3 9 H21 M9 3 L12 9 M15 3 L18 9 M10.5 12.5 L15 15 L10.5 17.5 Z"
    readonly property string search: "M17 10 A7 7 0 1 1 3 10 A7 7 0 1 1 17 10 Z M15.5 15.5 L21 21"
    readonly property string heart: "M12 20.5 C5 15.5 3 11.5 3 8.5 C3 5.8 5 4 7.5 4 C9.5 4 11.2 5.2 12 7 C12.8 5.2 14.5 4 16.5 4 C19 4 21 5.8 21 8.5 C21 11.5 19 15.5 12 20.5 Z"
    readonly property string comment: "M12 3 C7 3 3 6.6 3 11 C3 13.2 4 15.2 5.7 16.6 L4.5 21 L9.2 18.9 C10.1 19.1 11 19.2 12 19.2 C17 19.2 21 15.6 21 11.2 C21 6.7 17 3 12 3 Z"
    readonly property string send: "M21 3 L10 14 M21 3 L14 21 L10 14 L3 10 Z"
    readonly property string plus: "M5 3 H19 A2 2 0 0 1 21 5 V19 A2 2 0 0 1 19 21 H5 A2 2 0 0 1 3 19 V5 A2 2 0 0 1 5 3 Z M12 8 V16 M8 12 H16"
    readonly property string user: "M16 8 A4 4 0 1 1 8 8 A4 4 0 1 1 16 8 Z M4 21 C4 16.5 7.5 14 12 14 C16.5 14 20 16.5 20 21"
    readonly property string logout: "M9 21 H5 A2 2 0 0 1 3 19 V5 A2 2 0 0 1 5 3 H9 M16 17 L21 12 L16 7 M21 12 H9"
    readonly property string play: "M7 4 L20 12 L7 20 Z"
    readonly property string close: "M5 5 L19 19 M19 5 L5 19"
    readonly property string upload: "M12 16 V4 M7 9 L12 4 L17 9 M4 15 V20 H20 V15"
    readonly property string volume: "M3 9 H7 L12 5 V19 L7 15 H3 Z M16 9 A4 4 0 0 1 16 15 M19 6 A8 8 0 0 1 19 18"
    readonly property string volumeOff: "M3 9 H7 L12 5 V19 L7 15 H3 Z M16 9 L22 15 M22 9 L16 15"
    readonly property string lock: "M5 11 H19 V21 H5 Z M8 11 V7 A4 4 0 0 1 16 7 V11"
    readonly property string spinner: "M12 3 A9 9 0 1 1 3 12"
}