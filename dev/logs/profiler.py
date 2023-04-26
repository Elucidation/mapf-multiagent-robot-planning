"""read logs and profile

Measure things including:

world_sim when step starts, histogram of how long it takes, histogram of time between steps

Count of robot collision errors, and when they happened

gantt chart of when world_sim (ws) steps go, versus when robot_allocator (ra) updates
"""
import re
import matplotlib.pyplot as plt  # type: ignore
import numpy as np
import datetime
from matplotlib.backends.backend_pdf import PdfPages  # type: ignore


def load_log_file(filename):
    # Expect to run everything locally within this directory
    data = []
    with open(filename, 'r', encoding='utf8') as file:
        for line in file.readlines():
            parts = line.split(' - ')
            if len(parts) >= 3:
                data.append({
                    'Date': datetime.datetime.strptime(parts[0].strip(), '%Y-%m-%d %H:%M:%S,%f'),
                    'Type': parts[1].strip(),
                    'Message': parts[2].strip()
                })
    return data


def get_world_sim_stats(filename):
    data_world_sim: list[dict] = load_log_file(filename)
    # Get all update duration
    update_durations_list = []
    for entry in data_world_sim:
        if entry['Type'] == 'DEBUG' and entry['Message'].startswith('Step end'):
            match = re.search(r'took (\d.\d+) sec', entry['Message'])
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
        elif entry['Type'] == 'ERROR' and 'collision' in entry['Message']:
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
    subset_n = 200

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


def get_robot_allocator_stats(filename, offset_sec=0):
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
            # update end, took 0.002030 sec
            match = re.search(r'took (\d+.\d+) sec', entry['Message'])
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

    subset_n = 200

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
LOG_FOLDER = 'logs3'
OUTPUT_FILENAME = f'{LOG_FOLDER}/profiler_result_{LOG_FOLDER}.pdf'


stats_world_sim = get_world_sim_stats(f'{LOG_FOLDER}/world_sim.log')
offset_sec = stats_world_sim['step_starts'][0] # First timestamp of starts
stats_robot_allocator = get_robot_allocator_stats(f'{LOG_FOLDER}/robot_allocator.log', offset_sec=offset_sec)

set_update = stats_world_sim['update']
set_sleep = stats_world_sim['sleep']
ra_set_update = stats_robot_allocator['update']


def make_step_gantt():
    y_positions1 = np.zeros(len(set_update['labels']))
    y_positions2 = np.ones(len(ra_set_update['labels']))

    for positions, event_set in zip(
        [y_positions1,  y_positions2],
            [set_update,  ra_set_update]):
        plt.barh(positions, event_set['durations'],
                 left=event_set['starts'], height=0.5, label=event_set['label'])

    # Set x ticks to event labels
    plt.yticks([0, 1], ['World Sim', 'Robot\nAllocator'])
    plt.xticks(set_update['starts'], [
               f'T={label}, {t_start:.2f} ms' for t_start, label in zip(set_update['starts'], set_update['labels'])],
               fontsize=4, rotation='vertical')

    # Add lines for step start, keep ylim the same
    bot, top = plt.ylim()
    # plt.vlines(set_update['starts'], ymin=bot, ymax=top,
    #            linestyles='dotted', color='black', label='Step Start',
    #            linewidth=0.1
    #            )
    plt.ylim(bot, top)
    
    # plt.xlabel(f"Step # RA update_mean={ra_durations.mean():.4f} ms std={ra_durations.std():.4f}")
    plt.xlabel("Step #")
    plt.ylabel('Events')
    plt.title('Step Timeline')
    plt.legend()
    plt.grid(linestyle='dotted', linewidth=0.1)


collisions = stats_world_sim['collisions']
print(f'Number of collisions: {len(collisions)}\n: {collisions}')

with PdfPages(OUTPUT_FILENAME) as pdf:
    # Step durations
    plt.figure()
    plt.hist(set_update['durations_full'] * 1000)
    plt.xlabel('Update duration (ms)')
    plt.title('world_sim Update durations')
    pdf.savefig()

    # Step start times
    plt.figure()
    total_step_durations_ms = stats_world_sim['total_step_durations_ms']
    plt.hist(total_step_durations_ms)
    plt.xlabel(
        f'Total Step durations (ms) mean={total_step_durations_ms.mean()} ms std={total_step_durations_ms.std():.3f}')
    plt.title('world_sim Total Step duration (Total Step = Update + Sleep)')
    pdf.savefig()

    # Estimate sleep time by taking the time between step starts and subtract the calculated step duration from them
    step_starts_0_start = stats_world_sim['step_starts_0_start']
    update_durations = set_update['durations_full']
    sleep_estimates = np.diff(step_starts_0_start) - update_durations[:-1]
    plt.figure()
    plt.hist(sleep_estimates * 1000)
    plt.xlabel('Step sleep estimate (ms)')
    plt.title('world_sim estimated sleep between steps')
    pdf.savefig()

    # Gantt
    plt.figure(figsize=(25, 5))
    make_step_gantt()
    pdf.savefig()

    # Robot Allocator update step histogram
    plt.figure(figsize=(5,5))
    ra_durations = ra_set_update['durations_full']
    print(ra_durations.mean(), ra_durations.std(), ra_durations.min(), ra_durations.max())
    plt.hist(ra_durations * 1000)
    plt.xlabel(
        f'Update step durations (ms)\nmean={ra_durations.mean()*1000:.4f} ms std={ra_durations.std()*1000:.4f} ms')
    plt.title('Robot Allocator Update duration')
    pdf.savefig()