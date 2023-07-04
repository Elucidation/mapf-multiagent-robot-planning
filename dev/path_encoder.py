"""Encode/Decode paths from list of positions to a string set of directions ex. 'UDLRW' and back."""


class PathEncoder:
    """Encode/Decode paths into sets of directions.

    Example:
    Original: [(1, 1), (1, 2), (2, 2), (2, 2), (2, 1), (1, 1)]

    Encoded (5 chars): URWDL
    vs. JSON dumps (48 chars): [[1, 1], [1, 2], [2, 2], [2, 2], [2, 1], [1, 1]]
    Size ratio: 10.42%
    """
    MOVE_MAP = {
        'R': (1, 0),
        'L': (-1, 0),
        'U': (0, 1),
        'D': (0, -1),
        'W': (0, 0)
    }

    @staticmethod
    def get_direction(pos_a, pos_b) -> str:
        """Returns R-right, L-left, U-up, D-down, W-wait directions between two positions.
        This assumes the two positions are neighbors and are in only 1 of those directions."""
        dx, dy = pos_b[0] - pos_a[0], pos_b[1] - pos_a[1]
        return 'R' if dx > 0 else 'L' if dx < 0 else 'U' if dy > 0 else 'D' if dy < 0 else 'W'

    @staticmethod
    def encode_path(start_pos, path) -> str:
        if len(path) == 0:
            return ''
        return PathEncoder.get_direction(start_pos, path[0]) + ''.join(
            PathEncoder.get_direction(path[i], path[i + 1]) for i in range(len(path) - 1))

    @staticmethod
    def decode_path(start_pos, directions: str):
        """Returns path moving from start position, not including. """
        positions = []
        for direction in directions:
            dx, dy = PathEncoder.MOVE_MAP[direction]
            if len(positions) > 0:
                x, y = positions[-1]  # Get last position
            else:
                x, y = start_pos
            positions.append((x + dx, y + dy))
        return positions


if __name__ == "__main__":
    original_path = [(1, 2), (2, 2), (2, 2), (2, 1), (1, 1)]
    start = (1, 1)

    encoded_path = PathEncoder.encode_path(start, original_path)
    import json
    json_path = json.dumps(original_path)

    print(f'Original: {original_path}')
    print(f'\nEncoded ({len(encoded_path)} chars): {encoded_path}')
    print(f'vs. JSON dumps ({len(json_path)} chars): {json_path}')
    print(
        f'Size ratio: {float(len(encoded_path)) / float(len(json_path)) * 100:.2f}%')

    decoded_path = PathEncoder.decode_path(start, encoded_path)
    print(f'\nDecoded: {decoded_path}')
    assert (decoded_path == original_path)

    print(f'Empty: {PathEncoder.encode_path(start, [])}')
    print(f'Decode: {PathEncoder.decode_path(start, "")}')
