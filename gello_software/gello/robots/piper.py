import threading
import time
from typing import Dict, Optional, Sequence

import numpy as np

from gello.robots.robot import Robot


class PiperROSRobot(Robot):
    """Piper arm adapter that commands AgxArmRosNode through ROS 2 topics.

    This class is meant to be used as a GELLO ``Robot`` backend. Calls to
    ``command_joint_state`` publish a ``sensor_msgs/JointState`` message to the
    AGX ROS node, and feedback from ``feedback/joint_states`` is cached for
    ``get_joint_state`` and ``get_observations``.
    """

    def __init__(
        self,
        joint_names: Optional[Sequence[str]] = None,
        command_topic: str = "/control/joint_states",
        feedback_topic: str = "/feedback/joint_states",
        tcp_pose_topic: str = "/feedback/tcp_pose",
        node_name: str = "gello_piper_robot",
        wait_for_feedback: bool = True,
        feedback_timeout: float = 5.0,
        auto_enable: bool = False,
        open_control_gate: bool = False,
    ):
        import rclpy
        from geometry_msgs.msg import PoseStamped
        from rclpy.node import Node
        from sensor_msgs.msg import JointState
        from std_srvs.srv import SetBool

        self._rclpy = rclpy
        self._JointState = JointState
        self._PoseStamped = PoseStamped
        self._SetBool = SetBool

        if not rclpy.ok():
            rclpy.init(args=None)

        self._node: Node = rclpy.create_node(node_name)
        self._feedback_topic = feedback_topic
        self._joint_names = list(joint_names or self.default_joint_names())
        
        self._num_dofs = len(self._joint_names)
        self._joint_state = np.zeros(self._num_dofs)
        self._joint_velocities = np.zeros(self._num_dofs)
        self._joint_efforts = np.zeros(self._num_dofs)
        self._ee_pos_quat = np.zeros(7)

        self._last_feedback_time: Optional[float] = None

        self._stop_event = threading.Event()
        self._lock = threading.Lock()

        self._command_pub = self._node.create_publisher(
            JointState, command_topic, 10
        )

        self._node.create_subscription(
            JointState, feedback_topic, self._joint_state_callback, 10
        )
        self._node.create_subscription(
            PoseStamped, tcp_pose_topic, self._tcp_pose_callback, 10
        )

        self._spin_thread = threading.Thread(target=self._spin, daemon=True)
        self._spin_thread.start()

        if auto_enable:
            self.set_arm_enabled(True)
        if open_control_gate:
            self.set_control_enabled(True)
        if wait_for_feedback:
            self.wait_for_feedback(feedback_timeout)

    @staticmethod
    def default_joint_names() -> Sequence[str]:
        return ("joint1", "joint2", "joint3", "joint4", "joint5", "joint6", "gripper")

    def num_dofs(self) -> int:
        return self._num_dofs

    def get_joint_state(self) -> np.ndarray:
        with self._lock:
            return self._joint_state.copy()

    def command_joint_state(self, joint_state: np.ndarray) -> None:
        joint_state = np.asarray(joint_state, dtype=float)
        if len(joint_state) != self._num_dofs:
            raise ValueError(
                f"Expected joint state of length {self._num_dofs}, "
                f"got {len(joint_state)}."
            )

        msg = self._JointState()
        msg.header.stamp = self._node.get_clock().now().to_msg()
        msg.name = list(self._joint_names)
        msg.position = joint_state.tolist()
        msg.velocity = []
        msg.effort = []
        self._command_pub.publish(msg)

    def get_observations(self) -> Dict[str, np.ndarray]:
        with self._lock:
            return {
                "joint_positions": self._joint_state.copy(),
                "joint_velocities": self._joint_velocities.copy(),
                "joint_efforts": self._joint_efforts.copy(),
                "ee_pos_quat": self._ee_pos_quat.copy(),
                "gripper_position": np.array(0),
            }

    def wait_for_feedback(self, timeout: float = 5.0) -> None:
        start_time = time.time()
        while self._last_feedback_time is None:
            if time.time() - start_time > timeout:
                raise TimeoutError(
                    "Timed out waiting for Piper feedback on "
                    "feedback/joint_states. Is AgxArmRosNode running?"
                )
            time.sleep(0.01)

    def set_arm_enabled(self, enabled: bool, timeout: float = 2.0) -> bool:
        return self._call_set_bool_service("/enable_agx_arm", enabled, timeout)

    def set_control_enabled(self, enabled: bool, timeout: float = 2.0) -> bool:
        return self._call_set_bool_service("/control_enable", enabled, timeout)

    def close(self) -> None:
        self._stop_event.set()
        self._spin_thread.join(timeout=1.0)
        self._node.destroy_node()

    def _spin(self) -> None:
        while self._rclpy.ok() and not self._stop_event.is_set():
            self._rclpy.spin_once(self._node, timeout_sec=0.1)

    def _joint_state_callback(self, msg) -> None:
        positions = self._extract_named_values(msg.name, msg.position)
        velocities = self._extract_named_values(msg.name, msg.velocity)
        efforts = self._extract_named_values(msg.name, msg.effort)
        with self._lock:
            self._joint_state = positions
            self._joint_velocities = velocities
            self._joint_efforts = efforts
            self._last_feedback_time = time.time()

    def _tcp_pose_callback(self, msg) -> None:
        pose = msg.pose
        pos_quat = np.array(
            [
                pose.position.x,
                pose.position.y,
                pose.position.z,
                pose.orientation.x,
                pose.orientation.y,
                pose.orientation.z,
                pose.orientation.w,
            ],
            dtype=float,
        )
        with self._lock:
            self._ee_pos_quat = pos_quat

    def _extract_named_values(self, names, values) -> np.ndarray:
        values_by_name = {
            name: values[index]
            for index, name in enumerate(names)
            if index < len(values)
        }
        return np.array(
            [values_by_name.get(name, 0.0) for name in self._joint_names],
            dtype=float,
        )

    def _call_set_bool_service(
        self, service_name: str, value: bool, timeout: float
    ) -> bool:
        client = self._node.create_client(self._SetBool, service_name)
        if not client.wait_for_service(timeout_sec=timeout):
            self._node.get_logger().warn(f"Service {service_name} is not available")
            return False

        request = self._SetBool.Request()
        request.data = value
        future = client.call_async(request)
        start_time = time.time()
        while not future.done():
            if time.time() - start_time > timeout:
                self._node.get_logger().warn(f"Timed out calling {service_name}")
                return False
            time.sleep(0.01)

        result = future.result()
        return bool(result and result.success)


def main():
    robot = PiperROSRobot(wait_for_feedback=False)
    print(robot)


if __name__ == "__main__":
    main()
