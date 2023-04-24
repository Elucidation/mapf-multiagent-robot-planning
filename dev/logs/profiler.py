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


def load_world_sim_log(filename='world_sim.log'):
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


data: list[dict] = load_world_sim_log()

# Get all update duration
update_durations_list = []
for entry in data:
    if entry['Type'] == 'DEBUG' and entry['Message'].startswith('Step end'):
        match = re.search(r'took (\d.\d+) sec', entry['Message'])
        if match and match.groups():
            update_durations_list.append(float(match.group(1)))
update_durations = np.array(update_durations_list)

# Histogram of step start times versus
step_start_list = []
step_end_list = []
step_idx_list = []
for entry in data:
    if entry['Type'] == 'DEBUG' and entry['Message'].startswith('Step start'):
        step_start_list.append(entry['Date'])
    if entry['Type'] == 'DEBUG' and entry['Message'].startswith('Step end'):
        step_end_list.append(entry['Date'])
        match = re.search(r'\sT=(\d+)\s', entry['Message'])
        assert match
        step_idx_list.append(int(match.group(1)))


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


def make_step_gantt():
    subset_n = 20

    # Event processing time for update
    set_update = {
        'label': 'Update',
        'starts': step_starts_0_start[:subset_n-1],
        'durations': np.array(update_durations)[:subset_n-1],
        'labels': step_idx_list[:subset_n-1]
    }

    # Event: sleep time (starts at step end, goes till next start)
    set_sleep = {
        'label': 'Sleep',
        'starts': step_ends_0_start[:subset_n-1],
        'stops': step_starts_0_start[1:subset_n],
        'labels': step_idx_list[:subset_n-1]
    }
    set_sleep['durations'] = set_sleep['stops'] - set_sleep['starts']

    # y_positions1 = np.zeros(len(set_update['labels']))
    # y_positions2 = np.zeros(len(set_sleep['labels']))

    for event_set in [set_update, set_sleep]:
        plt.barh(np.zeros_like(event_set['label']), event_set['durations'],
                 left=event_set['starts'], height=0.5, label=event_set['label'])

    # Set x ticks to event labels
    plt.yticks([0], [''])
    plt.xticks(set_update['starts'], [f'T={label}' for label in set_update['labels']])

    # Add lines for step start, keep ylim the same
    bot, top = plt.ylim()
    plt.vlines(set_update['starts'], ymin=bot, ymax=top,
               linestyles='dotted', color='black', label='Step Start')
    plt.ylim(bot, top)

    plt.xlabel('Step #')
    plt.ylabel('Events')
    plt.title('Step Timeline')
    plt.legend()


with PdfPages('profiler_result.pdf') as pdf:
    # Step durations
    plt.figure()
    plt.hist(update_durations * 1000)
    plt.xlabel('Update duration (ms)')
    plt.title('world_sim Update durations')
    pdf.savefig()

    # Step start times
    plt.figure()
    plt.hist(np.diff(step_starts_0_start)  * 1000)
    plt.xlabel('Total Step durations (ms)')
    plt.title('world_sim Total Step duration (Total Step = Update + Sleep)')
    pdf.savefig()

    # Estimate sleep time by taking the time between step starts and subtract the calculated step duration from them
    sleep_estimates = np.diff(step_starts_0_start) - update_durations[:-1]
    plt.figure()
    plt.hist(sleep_estimates * 1000)
    plt.xlabel('Step sleep estimate (ms)')
    plt.title('world_sim estimated sleep between steps')
    pdf.savefig()

    # Gantt
    plt.figure(figsize=(15, 3))
    make_step_gantt()
    pdf.savefig()
