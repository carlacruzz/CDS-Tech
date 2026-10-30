"""Behavioural checks for ownership memory and the strict contact threshold."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from starter.possession_v1 import PossessionTracker, contact_touches, keeper_distances, ball_out


def ball_path(points, near):
    """Observations from ball positions (metres); frames in `near` have track 7 at 0.5 m."""
    return [(f, 0, 7 if f in near else 3, .5 if f in near else 5.0, None, None, p)
            for f, p in enumerate(points)]


class PossessionV1Tests(unittest.TestCase):
    def test_uninitialised_until_close_control(self):
        tracker = PossessionTracker()
        self.assertEqual(tracker.update(0, 1, 41, 9.0)[0], 'X')
        self.assertEqual(tracker.update(1, 0, 2, .99)[0], 'H')

    def test_distant_opponent_does_not_steal_possession(self):
        tracker = PossessionTracker()
        tracker.update(0, 0, 2, .5)
        for frame in range(1, 76):
            self.assertEqual(tracker.update(frame, 1, 41, 8.8)[0], 'H')
        self.assertEqual(tracker.last_control, 0)
        self.assertEqual(tracker.track, 2)

    def test_two_rival_teammates_take_control_from_the_first(self):
        tracker = PossessionTracker()
        tracker.update(0, 0, 2, .5)
        self.assertEqual(tracker.update(5, 1, 41, .8), ('H', 'cambio_pendiente'))
        self.assertEqual(tracker.update(6, 1, 41, .7)[1], 'cambio_pendiente')  # same player again
        self.assertEqual(tracker.update(9, 1, 42, .6), ('A', 'cambio_equipo'))
        self.assertEqual((tracker.backfill, tracker.last_control), (5, 9))

    def test_rival_holding_ball_over_one_second_takes_control(self):
        tracker = PossessionTracker()
        tracker.update(0, 0, 2, .5)
        for frame in range(10, 35):  # 25 frames: exactly one second is not enough
            self.assertEqual(tracker.update(frame, 1, 41, .6)[0], 'H')
        self.assertEqual(tracker.update(35, 1, 41, .6), ('A', 'cambio_por_control'))
        self.assertEqual(tracker.backfill, 10)

    def test_missing_ball_does_not_interrupt_hold_but_losing_it_does(self):
        tracker = PossessionTracker()
        tracker.update(0, 0, 2, .5)
        for frame in range(10, 20):
            tracker.update(frame, 1, 41, .6)
        tracker.update(20)  # ball not observed
        for frame in range(21, 35):
            tracker.update(frame, 1, 41, .6)
        self.assertEqual(tracker.update(35, 1, 41, .6)[1], 'cambio_por_control')
        tracker = PossessionTracker()
        tracker.update(0, 0, 2, .5)
        for frame in range(10, 30):
            tracker.update(frame, 1, 41, .6)
        tracker.update(30, 1, 41, 2.5)  # ball observed but not under one metre
        for frame in range(31, 40):
            self.assertEqual(tracker.update(frame, 1, 41, .6)[0], 'H')
        self.assertEqual(tracker.pending, (1, 41, 10))  # change would still start at frame 10

    def test_missing_ball_is_dead_and_keeps_pending_change(self):
        tracker = PossessionTracker()
        tracker.update(0, 1, 31, .5)
        tracker.update(10, 0, 4, .7)  # one rival touch, then the ball vanishes for 1 s
        for frame in range(11, 36):
            self.assertEqual(tracker.update(frame), ('D', 'balon_no_detectado'))
        self.assertEqual(tracker.update(36, 0, 24, .8), ('H', 'cambio_equipo'))  # pass from T4, remembered
        self.assertEqual(tracker.backfill, 10)

    def test_possessor_track_vanishing_keeps_possession(self):
        tracker = PossessionTracker()
        tracker.update(0, 0, 9, .4)
        # T9 disappears: the nearest is now a rival, first far, then a single touch
        self.assertEqual(tracker.update(1, 1, 45, 2.0), ('H', 'mantener_sin_contacto'))
        self.assertEqual(tracker.update(2, 1, 45, .8), ('H', 'cambio_pendiente'))
        self.assertEqual(tracker.update(3, 1, 45, 1.5), ('H', 'mantener_sin_contacto'))
        self.assertEqual(tracker.track, 9)

    def test_ball_passing_by_at_steady_speed_is_not_a_touch(self):
        straight = [(i * .4, 30.) for i in range(30)]           # 10 m/s, same direction
        self.assertEqual(contact_touches(ball_path(straight, {14, 15}), 1.0)[14], False)
        slowing = [(sum(.4 * .99 ** j for j in range(i)), 30.) for i in range(30)]  # gentle deceleration
        self.assertEqual(contact_touches(ball_path(slowing, {14, 15}), 1.0)[14], False)

    def test_ball_turned_or_stopped_is_a_touch(self):
        turned = [(i * .4, 30.) if i <= 15 else (6., 30. + (i - 15) * .4) for i in range(30)]
        self.assertTrue(contact_touches(ball_path(turned, {14, 15}), 1.0)[14])
        stopped = [(min(i, 15) * .4, 30.) for i in range(30)]
        self.assertTrue(contact_touches(ball_path(stopped, {14, 15}), 1.0)[15])
        missing = [None if i < 10 else (i * .4, 30.) for i in range(30)]
        self.assertIsNone(contact_touches(ball_path(missing, {14, 15}), 1.0)[14])

    def test_pass_needs_two_real_touches(self):
        tracker = PossessionTracker()
        tracker.update(0, 0, 2, .5)
        tracker.update(5, 1, 41, .8, touch=False)   # ball went past T41
        self.assertEqual(tracker.update(9, 1, 42, .6, touch=True), ('H', 'cambio_pendiente'))
        self.assertEqual(tracker.pending, (1, 42, 9))  # T42 becomes the first touch
        self.assertEqual(tracker.update(12, 1, 43, .6, touch=False), ('H', 'cambio_pendiente_sin_toque'))
        self.assertEqual(tracker.update(15, 1, 43, .6, touch=True), ('A', 'cambio_equipo'))
        self.assertEqual(tracker.backfill, 9)

    def test_single_rival_control_does_not_change_possession(self):
        tracker = PossessionTracker()
        tracker.update(0, 0, 2, .5)
        tracker.update(1, 1, 41, .8)
        self.assertEqual(tracker.update(2, 0, 3, .5), ('H', 'control_confirmado'))
        self.assertEqual(tracker.update(3, 1, 42, .6), ('H', 'cambio_pendiente'))  # restarts the count
        self.assertIsNone(tracker.backfill)

    def test_exactly_one_metre_does_not_confirm_control(self):
        tracker = PossessionTracker()
        tracker.update(0, 0, 2, .5)
        self.assertEqual(tracker.update(1, 1, 41, 1.0)[0], 'H')

    def test_missing_ball_is_dead_ball(self):
        tracker = PossessionTracker()
        self.assertEqual(tracker.update(0)[0], 'D')
        tracker.update(1, 1, 41, .4)
        self.assertEqual(tracker.update(2)[0], 'D')
        self.assertEqual(tracker.update(3, 1, 41, 5)[0], 'A')  # team remembered after the gap
        tracker.update(4, 0, 2, .4)
        self.assertEqual(tracker.update(5), ('D', 'balon_no_detectado'))  # pending change stays pending

    def test_new_half_resets_memory(self):
        tracker = PossessionTracker()
        tracker.update(0, 0, 2, .5)
        tracker.reset()
        self.assertEqual(tracker.update(1, 1, 41, 12)[0], 'X')

    def test_rival_closer_to_goal_than_keeper_does_not_take_control(self):
        tracker = PossessionTracker()
        tracker.update(0, 1, 41, .5)
        self.assertEqual(tracker.update(1, 0, 24, .4, 7.0, 9.0), ('A', 'cambio_bloqueado_portero'))
        self.assertEqual((tracker.track, tracker.last_control), (41, 0))

    def test_rival_farther_from_goal_than_keeper_takes_control(self):
        tracker = PossessionTracker()
        tracker.update(0, 1, 41, .5)
        tracker.update(1, 0, 2, .4, 30.0, 2.0)
        self.assertEqual(tracker.update(2, 0, 3, .4, 30.0, 2.0)[0], 'H')

    def test_no_keeper_in_area_allows_change(self):
        tracker = PossessionTracker()
        tracker.update(0, 1, 41, .5)
        tracker.update(1, 0, 2, .4, 3.0, None)
        self.assertEqual(tracker.update(2, 0, 3, .4, 3.0, None)[0], 'H')

    def test_vetoed_control_does_not_count_as_first_teammate(self):
        tracker = PossessionTracker()
        tracker.update(0, 1, 41, .5)
        tracker.update(1, 0, 24, .4, 7.0, 9.0)
        self.assertEqual(tracker.update(2, 0, 3, .4, 30.0, 2.0), ('A', 'cambio_pendiente'))

    def test_veto_never_applies_to_first_control_or_same_team(self):
        tracker = PossessionTracker()
        self.assertEqual(tracker.update(0, 0, 2, .5, 1.0, 9.0)[0], 'H')
        self.assertEqual(tracker.update(1, 0, 3, .5, 1.0, 9.0)[1], 'control_confirmado')

    def test_keeper_is_own_area_track_nearest_goal(self):
        pitch, teams, goal = (105.3, 68.0), [0, 0, 1], [0, 1]
        players = [(0, (.10, .30)), (1, (.03, .5)), (2, (.05, .5))]  # slot 2 is a rival in home's area
        home, away = keeper_distances(players, teams, goal, pitch)
        self.assertAlmostEqual(home, .03 * 105.3)
        self.assertIsNone(away)

    def test_dead_ball_behind_keeper_is_nobodys_control(self):
        tracker = PossessionTracker()
        tracker.update(0, 1, 41, .5)
        self.assertEqual(tracker.update(1, 0, 9, .3, ignored=True), ('A', 'control_ignorado_tras_portero'))
        self.assertIsNone(tracker.pending)
        tracker.update(2, 1, 41, .5)
        self.assertEqual(tracker.update(3, 1, 42, .4, ignored=True)[1], 'control_ignorado_tras_portero')
        self.assertEqual(tracker.track, 41)  # not even the same team's control counts
        fresh = PossessionTracker()
        self.assertEqual(fresh.update(0, 0, 9, .3, ignored=True)[0], 'X')

    def test_ignored_control_interrupts_a_hold(self):
        tracker = PossessionTracker()
        tracker.update(0, 0, 2, .5)
        for frame in range(10, 20):
            tracker.update(frame, 1, 41, .6)
        tracker.update(20, 1, 41, .6, ignored=True)
        for frame in range(21, 40):
            self.assertEqual(tracker.update(frame, 1, 41, .6)[0], 'H')

    def test_ball_out_of_pitch_not_slow_ball(self):
        pitch = (105.3, 68.0)
        points = [(10., 30.), (10., 30.), (-.8, 34.), (106., 34.), (50., -1.), (105.3, 68.), None]
        self.assertEqual(ball_out(ball_path(points, set()), pitch),
                         [False, False, True, True, True, False, False])  # still on the pitch is in play


if __name__ == '__main__':
    unittest.main()
