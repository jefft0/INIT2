import numpy as np

MIN_PLACE_CELL_DISTANCE = 300
ICP_DISTANCE_THRESHOLD = 100
ANGULAR_RESOLUTION = 1  # Degree
MASK_ARRAY = np.zeros(360 // ANGULAR_RESOLUTION, dtype=float)
MASK_ARRAY[:25 // ANGULAR_RESOLUTION] = 1
MASK_ARRAY[-25 // ANGULAR_RESOLUTION:] = 1
