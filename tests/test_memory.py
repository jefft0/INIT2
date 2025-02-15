import numpy as np
import pytest
from petitbrain.Memory.AllocentricMemory.AllocentricMemory import AllocentricMemory
from petitbrain.Memory.AllocentricMemory.Geometry import cell_to_point
from petitbrain.Memory import CELL_RADIUS

# Testing Allocentric Memory
# py -m autocat.Memory.AllocentricMemory

allocentric_memory = AllocentricMemory(8, 9, CELL_RADIUS)
# Displaying the hexagonal grid in the console.
print(allocentric_memory)


def test_cell_to_point():
    """Test the conversion of cell to point"""
    i_range = np.arange(1, 4)
    j_range = np.arange(1, 3)
    I, J = np.meshgrid(i_range, j_range, indexing='ij')
    result = cell_to_point(I, J)
    expected = np.array([[[75., 129.90381057],
                          [75., 216.50635095]],
                         [[150., 173.20508076],
                          [150., 259.80762114]],
                         [[225., 216.50635095],
                          [225., 303.10889132]]])
    np.testing.assert_allclose(result, expected)


def test_calculate_forward_pe(workspace_fixture):
    result = workspace_fixture.memory.body_memory.get_body_direction_normalized()
    np.testing.assert_allclose(np.array(result), np.array([0.8660254, 0.5, 0.]))
    assert workspace_fixture.memory.place_memory.forward_pe == 0


def test_cue(workspace_fixture):
    result = workspace_fixture.memory.place_memory.place_cells[1].cues[0].point()
    np.testing.assert_allclose(result, np.array([43.30127, 25., 0]))


@pytest.fixture
def forward_fixture(workspace_fixture):
    workspace_fixture.memory.place_memory.place_cells[1].point = np.array([0, 0, 0])
    workspace_fixture.memory.place_memory.place_cells[1].last_robot_point_in_cell = np.array([100, 0, 0])
    workspace_fixture.memory.place_memory.place_cells[2].point = np.array([400, 0, 0])
    workspace_fixture.memory.place_memory.position_pe = np.array([30, 0, 0])
    return workspace_fixture
