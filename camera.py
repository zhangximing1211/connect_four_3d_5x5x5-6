from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Tuple
from config import CAM_DIST, SCALE

def deg2rad(d: float) -> float:
    return d * math.pi / 180.0

@dataclass
class Camera:
    yaw_deg: float = 35.0
    pitch_deg: float = 25.0
    dist: float = CAM_DIST
    scale: float = SCALE

    def rotate(self, dyaw: float = 0.0, dpitch: float = 0.0):
        self.yaw_deg = (self.yaw_deg + dyaw) % 360.0
        self.pitch_deg = max(-80.0, min(80.0, self.pitch_deg + dpitch))

    def project(self, x: float, y: float, z: float, w: int, h: int) -> Tuple[int,int,float]:
        yaw = deg2rad(self.yaw_deg)
        pitch = deg2rad(self.pitch_deg)

        cy, sy = math.cos(yaw), math.sin(yaw)
        x1 = x * cy - y * sy
        y1 = x * sy + y * cy
        z1 = z

        cp, sp = math.cos(pitch), math.sin(pitch)
        y2 = y1 * cp - z1 * sp
        z2 = y1 * sp + z1 * cp
        x2 = x1

        depth = (self.dist - y2)
        if depth <= 0.2:
            depth = 0.2

        sx = (x2 / depth) * self.scale + w * 0.5
        sy = (-z2 / depth) * self.scale + h * 0.58
        return int(sx), int(sy), depth
