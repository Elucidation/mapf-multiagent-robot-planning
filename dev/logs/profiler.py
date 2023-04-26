"""read logs and profile

Measure things including:

world_sim when step starts, histogram of how long it takes, histogram of time between steps

Count of robot collision errors, and when they happened

gantt chart of when world_sim (ws) steps go, versus when robot_allocator (ra) updates
"""
import re
import datetime
import numpy as np
import matplotlib.pyplot as plt  # type: ignore
from matplotlib.backends.backend_pdf import PdfPages  # type: ignore


def load_log_file(filename):
    # Expect to run everything locally within this directory
    data = []
    with open(filename, 'r', encoding='utf8') as file:
        for line in file.readlines():
            parts = line.split(' - ')
            if len(parts) == 3:
                data.append({
                    'Date': datetime.datetime.strptime(parts[0].strip(), '%Y-%m-%d %H:%M:%S,%f'),
                    'Type': parts[1].strip(),
                    'Message': parts[2].strip()
                })
            elif len(parts) == 4:
                data.append({
                    'Date': datetime.datetime.strptime(parts[0].strip(), '%Y-%m-%d %H:%M:%S,%f'),
                    'Name': parts[1].strip(),
                    'Type': parts[2].strip(),
                    'Message': parts[3].strip()
                })
    return data


def get_world_sim_stats(filename, subset_n=None):
    data_world_sim: list[dict] = load_log_file(filename)
    # Get all update duration
    update_durations_list = []
    for entry in data_world_sim:
        if entry['Type'] == 'DEBUG' and entry['Message'].startswith('Step end'):
            match = re.search(r'took (\d+.\d+) ms', entry['Message'])
            if match and match.groups():
                update_durations_list.append(float(match.group(1)))
    update_durations = np.array(update_durations_list)

    # Histogram of step start times versus
    step_start_list = []
    step_end_list = []
    step_idx_list = []
    collisions = []
    for entry in data_world_sim:
        if entry['Type'] == 'DEBUG' and entry['Message'].startswith('Step start'):
            step_start_list.append(entry['Date'])
        elif entry['Type'] == 'DEBUG' and entry['Message'].startswith('Step end'):
            step_end_list.append(entry['Date'])
            match = re.search(r'\sT=(\d+)\s', entry['Message'])
            assert match
            step_idx_list.append(int(match.group(1)))
        elif entry['Type'] == 'ERROR' and 'Robot collision' in entry['Message']:
            collisions.append(entry)

    step_starts = np.array(step_start_list)
    step_ends = np.array(step_end_list)

    # Offset everything to zero start
    step_starts_0_start = step_starts - step_starts[0]
    step_ends_0_start = step_ends - step_starts[0]

    # dt_s = 0.1  # hard-coded
    # step_starts = np.fromiter((step.total_seconds() - dt_s * t for t, step in enumerate(step_starts)), dtype=np.float)
    step_starts_0_start = np.fromiter((step.total_seconds()
                                       for step in step_starts_0_start), dtype=float)

    step_ends_0_start = np.fromiter((step.total_seconds()
                                    for step in step_ends_0_start), dtype=float)
    if subset_n:
        subset_n = min(len(step_starts), subset_n)
    else:
        subset_n = len(step_starts)

    # Event processing time for update
    set_update = {
        'label': 'WS Update',
        'starts': step_starts_0_start[:subset_n-1],
        'durations': np.array(update_durations)[:subset_n-1],
        'durations_full': update_durations,
        'labels': step_idx_list[:subset_n-1]
    }

    # Event: sleep time (starts at step end, goes till next start)
    set_sleep = {
        'label': 'WS Sleep',
        'starts': step_ends_0_start[:subset_n-1],
        'stops': step_starts_0_start[1:subset_n],
        'labels': step_idx_list[:subset_n-1]
    }
    set_sleep['durations'] = set_sleep['stops'] - set_sleep['starts']

    return {
        'update': set_update,
        'sleep': set_sleep,
        'step_starts': step_starts,
        'step_starts_0_start': step_starts_0_start,
        'total_step_durations_ms': np.diff(step_starts_0_start) * 1000,
        'collisions': collisions
    }


def get_robot_allocator_stats(filename, offset_sec=0, subset_n=None):
    data_robot_allocator: list[dict] = load_log_file(filename)

    # Get all update duration
    update_durations_list = []
    step_starts_list = []
    step_ends_list = []
    # step/update start are at the same time
    # step/update end are at the same time, use update end to get timed duration
    for entry in data_robot_allocator:
        if 'Step start' in entry['Message']:
            step_starts_list.append(entry['Date'])
        elif 'update end' in entry['Message']:
            step_ends_list.append(entry['Date'])
            match = re.search(r'took (\d+.\d+) ms', entry['Message'])
            assert match
            update_durations_list.append(float(match.group(1)))

    update_durations = np.array(update_durations_list)
    step_starts = np.array(step_starts_list)
    step_ends = np.array(step_ends_list)

    # Offset everything to zero start
    step_starts_0_start = step_starts - offset_sec
    step_ends_0_start = step_ends - offset_sec

    # dt_s = 0.1  # hard-coded
    # step_starts = np.fromiter((step.total_seconds() - dt_s * t for t, step in enumerate(step_starts)), dtype=np.float)
    step_starts_0_start = np.fromiter((step.total_seconds()
                                       for step in step_starts_0_start), dtype=float)

    step_ends_0_start = np.fromiter((step.total_seconds()
                                    for step in step_ends_0_start), dtype=float)

    if subset_n:
        subset_n = min(len(step_starts), subset_n)
    else:
        subset_n = len(step_starts)

    # Event processing time for update
    set_update_ra = {
        'label': 'RA Update',
        'starts': step_starts_0_start[:subset_n-1],
        'durations': np.array(update_durations)[:subset_n-1],
        'durations_full': update_durations,
        'labels': range(subset_n-1)
    }
    return {
        'update': set_update_ra,
        # 'sleep': set_sleep,
        'step_starts_0_start': step_starts_0_start,
        'total_step_durations_ms': np.diff(step_starts_0_start) * 1000,
    }


##########################################################
# Main script
# LOG_FOLDER = 'logs9_A'
LOG_FOLDER = '..'
SAVE_PDF = True
OUTPUT_FILENAME = f'{LOG_FOLDER}/profiler_result_{LOG_FOLDER}.pdf'


SUBSET_N = 1520
stats_world_sim = get_world_sim_stats(
    f'{LOG_FOLDER}/world_sim.log', subset_n=SUBSET_N)
offset_sec = stats_world_sim['step_starts'][0]  # First timestamp of starts
stats_robot_allocator = get_robot_allocator_stats(
    f'{LOG_FOLDER}/robot_allocator.log', offset_sec=offset_sec, subset_n=SUBSET_N)

set_update = stats_world_sim['update']
set_sleep = stats_world_sim['sleep']
ra_set_update = stats_robot_allocator['update']


def make_step_gantt():
    bar_height = 0.2
    y_positions1 = np.zeros(len(set_update['labels']))
    y_positions2 = bar_height * np.ones(len(ra_set_update['labels']))

    for positions, event_set in zip(
        [y_positions1,  y_positions2],
            [set_update,  ra_set_update]):
        plt.barh(positions, event_set['durations'] / 1000.0,  # Need durations in seconds
                 left=event_set['starts'], height=bar_height, label=event_set['label'])

    # Set x ticks to event labels
    plt.yticks([0, bar_height], ['World Sim', 'Robot\nAllocator'])
    plt.xticks(set_update['starts'], [
               f'T={label}, {t_start:.2f} ms' for t_start, label in zip(set_update['starts'], set_update['labels'])],
               fontsize=4, rotation='vertical')

    # Add vertical lines at the time step when world state was invalid / had collision
    bot, top = plt.ylim()
    offset_sec = stats_world_sim['step_starts'][0]
    collision_x_pts = [(collision['Date'] - offset_sec).total_seconds()
                       for collision in stats_world_sim['collisions']]
    plt.vlines(collision_x_pts, ymin=bot, ymax=top,
               linestyles='dotted', color='red', label='Step Start',
               linewidth=0.5
               )
    plt.ylim(bot, top)

    # plt.xlabel(f"Step # RA update_mean={ra_durations.mean():.4f} ms std={ra_durations.std():.4f}")
    plt.xlabel("Step #")
    plt.ylabel('Events')
    plt.title(f'Step Timeline - {len(collisions)} collisions')
    plt.legend()
    plt.grid(linestyle='dotted', linewidth=0.1)


collisions = stats_world_sim['collisions']

total_step_durations_ms = stats_world_sim['total_step_durations_ms']
ws_update = set_update['durations_full']
ws_update_mean = set_update['durations_full'].mean()
ws_total_step_mean = total_step_durations_ms.mean()
ra_durations = ra_set_update['durations_full']

print(f'Logs: {LOG_FOLDER}')
print(f'Number of collisions: {len(collisions)}')
print(
    f'WS total step duration mean {total_step_durations_ms.mean():.2f} '
    f'[{total_step_durations_ms.min():.2f} - {total_step_durations_ms.max():.2f}], '
    f'std {total_step_durations_ms.std():.2f} ms')
print(
    f'WS update duration mean {ws_update.mean():.2f} '
    f'[{ws_update.min():.2f} - {ws_update.max():.2f}], '
    f'std {ws_update.std():.2f} ms')
print(
    f'RA update duration mean {ra_durations.mean():.2f} '
    f'[{ra_durations.min():.2f} - {ra_durations.max():.2f}], std {ra_durations.std():.2f} ms')


if SAVE_PDF:
    with PdfPages(OUTPUT_FILENAME) as pdf:
        # WS Step durations
        plt.figure(figsize=(15, 5))
        plt.subplot(121)
        plt.hist(set_update['durations_full'], bins=40, alpha=0.5, label='WS')
        # plt.xlabel('Update duration (ms)')
        # plt.title('world_sim Update durations')
        # Robot Allocator update step histogram
        plt.subplot(121)
        plt.hist(ra_durations, bins=40, alpha=0.5, label='RA')
        min_ylim, max_ylim = plt.ylim()
        # Mean line for WS
        plt.axvline(ws_update_mean, color='blue', linestyle='dashed')
        plt.text(ws_update_mean, max_ylim*0.9,
                 f' WS Mean - {ws_update_mean:.2f} ms', fontsize=6)
        # Mean line for RA
        plt.axvline(ra_durations.mean(), color='orange', linestyle='dashed')
        plt.text(ra_durations.mean(), max_ylim*0.8,
                 f' RA Mean - {ra_durations.mean():.2f} ms', fontsize=6)

        plt.xlabel(
            f'Update step durations (ms)\nRA mean={ra_durations.mean():.2f} ms '
            f'std={ra_durations.std():.2f} ms')
        plt.title('World Sim vs Robot Allocator Update durations')
        plt.legend(loc='upper right')

        # WS Total Step durations
        plt.subplot(122)
        plt.hist(total_step_durations_ms)
        min_ylim, max_ylim = plt.ylim()
        plt.axvline(100.0, color='black', linestyle='dashed')
        plt.text(100, max_ylim*0.9, ' Desired Step - 100 ms', fontsize=6)
        plt.axvline(ws_total_step_mean, color='red', linestyle='dashed')
        plt.text(ws_total_step_mean, max_ylim*0.9,
                 f' Mean Step - {ws_total_step_mean:.2f} ms', fontsize=6)
        plt.xlabel(
            f'Total Step durations (ms)\n'
            f'WS mean={ws_total_step_mean:.2f} ms std={total_step_durations_ms.std():.2f}')
        plt.title('World Sim Total Step duration (Total Step = Update + Sleep)')

        plt.tight_layout()
        pdf.savefig()

        # Gantt
        plt.figure(figsize=(25, 5))
        make_step_gantt()
        plt.tight_layout()
        pdf.savefig()
