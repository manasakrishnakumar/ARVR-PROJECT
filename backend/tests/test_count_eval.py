import pytest

from app.exercises.library import get_exercise
from app.ml.count_eval import Block, auto_range, detect, evaluate_blocks, match
from app.synthetic.sequences import make_sequence

ELBOW = get_exercise("elbow_flexion")  # illustrative 160 -> 50
ABD = get_exercise("shoulder_abduction")  # illustrative 20 -> 90


def test_match_is_one_to_one_by_overlap():
    truth = [(0, 100), (120, 220), (240, 340)]
    assert match(truth, [(5, 105), (118, 225), (500, 600)]) == 2  # third detection overlaps nothing
    assert match(truth, [(0, 100), (10, 90)]) == 1  # two detections cannot claim the same labelled repetition
    assert match(truth, []) == 0 and match([], truth) == 0
    assert match([(0, 100)], [(60, 160)]) == 0  # IoU below 0.5


def test_auto_range_uses_only_the_data_and_the_movement_direction():
    seq = [a for _, a in make_sequence(20, 70, 6)]
    start, target = auto_range(seq, ABD)  # increasing exercise
    assert start < target and 15 < start < 35 and 55 < target < 75
    start, target = auto_range([a for _, a in make_sequence(170, 100, 6)], ELBOW)  # decreasing exercise
    assert start > target
    assert auto_range([90.0] * 200, ABD) is None  # no movement: refuse to calibrate
    assert auto_range([None] * 200, ABD) is None


def _block(start, target, n, ex, depth=1.0):
    seq = make_sequence(start, target, n, period_s=3, fps=30, depth=depth, rest_s=1.0)
    angles = [a for _, a in seq]
    per = 3 * 30 + 30
    truth = [(30 + i * per, 30 + i * per + 90) for i in range(n)]  # labelled spans of each excursion
    return Block("synthetic", ex, angles, 0, truth)


def test_detect_finds_every_clean_excursion():
    b = _block(160, 50, 5, ELBOW)
    found = detect(b.angles, 160, 50, 0.6, 8.0)
    assert len(found) == 5 and all(reached for *_, reached in found)


def test_illustrative_thresholds_fail_when_the_real_range_differs_but_auto_calibration_recovers():
    # this person's abduction only spans 40 -> 70 degrees in the image, but the app assumes 20 -> 90
    b = _block(40, 70, 6, ABD)
    res = evaluate_blocks([b])
    assert res["illustrative"]["detected_repetitions"] < 6  # the assumed range is never reached
    assert res["auto"]["detected_repetitions"] == 6 and res["auto"]["f1"] > 0.9 and res["auto"]["mean_absolute_count_error"] == 0


def test_evaluation_handles_blocks_without_movement_and_empty_input():
    flat = Block("synthetic", ABD, [50.0] * 300, 0, [(30, 120)])
    res = evaluate_blocks([flat])
    assert res["auto"]["blocks_skipped_no_calibration"] == 1 and res["auto"]["blocks"] == 0
    assert evaluate_blocks([])["auto"]["f1"] == 0.0


def test_block_offset_is_applied_once_so_intervals_still_match():
    b = _block(160, 50, 5, ELBOW)
    shifted = Block("synthetic", ELBOW, b.angles, 500, [(a + 500, z + 500) for a, z in b.truth])  # same data, block starts at frame 500
    r0, r1 = evaluate_blocks([b])["illustrative"], evaluate_blocks([shifted])["illustrative"]
    assert r1["matched"] == r0["matched"] == 5 and r1["f1"] == pytest.approx(1.0)


def test_metrics_aggregate_over_blocks():
    res = evaluate_blocks([_block(160, 50, 5, ELBOW), _block(160, 50, 4, ELBOW)])
    a = res["illustrative"]
    assert a["labelled_repetitions"] == 9 and a["detected_repetitions"] == 9 and a["mean_absolute_count_error"] == 0
    assert a["exact_count_fraction"] == 1.0 and a["precision"] == pytest.approx(1.0) and a["recall"] == pytest.approx(1.0)
