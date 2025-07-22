from django.dispatch import Signal

follow_done = Signal(["follower", "following"])
unfollow_done = Signal(["follower", "following"])
