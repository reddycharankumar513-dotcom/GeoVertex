import * as Cesium from 'cesium';

export interface CameraPreset {
  destination: [number, number, number];
  orientation?: { heading: number; pitch: number; roll: number };
}

export const cameraService = {
  /**
   * Fly camera to building 3D location with a gentle perspective angle.
   */
  flyToBuilding: (
    viewer: Cesium.Viewer,
    centroid: [number, number, number] | [number, number],
    height: number = 25.0
  ) => {
    if (!viewer || viewer.isDestroyed()) return;

    const lon = centroid[0];
    const lat = centroid[1];
    const baseHeight = centroid[2] || 0;
    const viewAltitude = Math.max(height * 2.5, 120);

    const destination = Cesium.Cartesian3.fromDegrees(
      lon,
      lat - 0.0018, // slight offset south to look north-facing
      baseHeight + viewAltitude
    );

    viewer.camera.flyTo({
      destination,
      orientation: {
        heading: Cesium.Math.toRadians(0.0),
        pitch: Cesium.Math.toRadians(-35.0),
        roll: 0.0,
      },
      duration: 1.5,
    });
  },

  /**
   * Fly camera to parcel boundary centroid.
   */
  flyToParcel: (
    viewer: Cesium.Viewer,
    centroid: [number, number, number] | [number, number],
    altitude: number = 320.0
  ) => {
    if (!viewer || viewer.isDestroyed()) return;

    const destination = Cesium.Cartesian3.fromDegrees(
      centroid[0],
      centroid[1] - 0.0025,
      altitude
    );

    viewer.camera.flyTo({
      destination,
      orientation: {
        heading: Cesium.Math.toRadians(0.0),
        pitch: Cesium.Math.toRadians(-45.0),
        roll: 0.0,
      },
      duration: 1.5,
    });
  },

  /**
   * Reset camera to scene default center coordinates.
   */
  resetCamera: (
    viewer: Cesium.Viewer,
    center: [number, number, number] = [78.489, 17.383, 400.0]
  ) => {
    if (!viewer || viewer.isDestroyed()) return;

    viewer.camera.flyTo({
      destination: Cesium.Cartesian3.fromDegrees(center[0], center[1] - 0.003, center[2] || 450.0),
      orientation: {
        heading: Cesium.Math.toRadians(0.0),
        pitch: Cesium.Math.toRadians(-45.0),
        roll: 0.0,
      },
      duration: 1.5,
    });
  },
};
