/** CPU geometry checks; does not create a GPU renderer or establish visual acceptance. */
import { test } from "node:test";
import assert from "node:assert/strict";
import * as THREE from "three";
import { CityScene } from "../src/scene.ts";
import type { Network } from "../src/types.ts";
const network: Network = {
  schema_version: "1.0",
  network_hash: "n",
  origin: {},
  lanes: [
    {
      id: "l",
      edge_id: "e",
      shape: [
        [0, 0],
        [100, 0],
      ],
      width: 3,
      speed: 10,
      display_elevation: 5,
    },
    {
      id: ":j",
      edge_id: ":j",
      shape: [
        [100, 0],
        [102, 2],
      ],
      width: 3,
      speed: 10,
    },
  ],
  buildings: [
    {
      id: "b",
      polygon: [
        [20, 20],
        [30, 20],
        [30, 30],
        [20, 30],
      ],
      height: 12,
    },
  ],
  junctions: [
    {
      id: "j",
      position: [100, 0],
      shape: [
        [98, -2],
        [104, -2],
        [104, 4],
        [98, 4],
      ],
    },
  ],
  gates: [],
  core_polygon: [
    [-500, -500],
    [500, -500],
    [500, 500],
    [-500, 500],
  ],
  simulation_polygon: [
    [-1000, -1000],
    [1000, -1000],
    [1000, 1000],
    [-1000, 1000],
  ],
};
function fixture() {
  const city = Object.create(CityScene.prototype) as {
    network: Network;
    scene: THREE.Scene;
    buildings: THREE.Group;
    roads: THREE.Group;
    picker: THREE.Mesh[];
    buildCity: () => void;
  };
  Object.assign(city, {
    network,
    scene: new THREE.Scene(),
    buildings: new THREE.Group(),
    roads: new THREE.Group(),
    picker: [],
  });
  city.buildCity();
  return city;
}
test("roads, internal connections and junction polygons successfully merge with compatible attributes", () => {
  const city = fixture();
  assert.equal(city.roads.children.length, 3);
  assert.equal(city.picker.length, 3);
  for (const object of city.roads.children) {
    const geometry = (object as THREE.Mesh).geometry;
    assert.ok(geometry.getAttribute("position").count > 0);
    assert.ok(
      Array.from(geometry.getAttribute("position").array).every(
        Number.isFinite,
      ),
    );
  }
  const road = city.roads.children[0] as THREE.Mesh;
  road.geometry.computeBoundingBox();
  assert.ok(road.geometry.boundingBox!.min.y >= 5);
});
test("building extrusion uses east X, up Y, north negative Z without inversion", () => {
  const city = fixture(),
    mesh = city.buildings.children[0] as THREE.Mesh;
  mesh.geometry.computeBoundingBox();
  const box = mesh.geometry.boundingBox!;
  assert.ok(Math.abs(box.min.x - 20) < 0.001);
  assert.ok(Math.abs(box.max.x - 30) < 0.001);
  assert.ok(Math.abs(box.min.y) < 0.001);
  assert.ok(Math.abs(box.max.y - 12) < 0.001);
  assert.ok(Math.abs(box.min.z + 30) < 0.001);
  assert.ok(Math.abs(box.max.z + 20) < 0.001);
});
