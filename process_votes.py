from database import get_user_data


def count_votes(group_chat_id, voted_users):
    votes = {}

    for user_id in voted_users:
        choice = get_user_data(user_id, group_chat_id, "choice")

        if choice is not None:
            if choice in votes:
                votes[choice] += 1

            else:
                votes[choice] = 1

    if votes.values():
        max_votes = max(votes.values())

    else:
        max_votes = 0

    killed_player = [player for player, votes in votes.items() if votes == max_votes]

    if len(killed_player) != 1:
        killed_player = None

    else:
        killed_player = killed_player[0]

    return killed_player
