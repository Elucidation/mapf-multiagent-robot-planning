"""[DEV] Counts log messages of generate_path and times from them
Then it builds a histogram comparison between two heuristic functions (euclidean vs true). """
import numpy as np
import matplotlib.pyplot as plt  # type: ignore


def load_robot_allocator_log_file(filename) -> list[dict]:
    # Expect to run everything locally within this directory
    data = []
    with open(filename, 'r', encoding='utf8') as file:
        for line in file:
            parts = line.split(' - ')
            if not 'generate_path' in parts[3]:
                continue
            if 'Robot Allocator started' in parts[3]:
                # Delete everything prior
                data = []
                continue

            # example message contains 'generate_path took 0.387 ms'
            _, _, duration_ms_str, _ = parts[3].split(' ')
            data.append(float(duration_ms_str))
    return np.array(data)


print('Loading data')
# data_euclid = load_robot_allocator_log_file(
#     'curr/TEST1_robot_allocator_EUCLIDEAN.log')
data_true_d = load_robot_allocator_log_file(
    'curr/robot_allocator.log')
data_true_a = load_robot_allocator_log_file(
    'curr/robot_allocator.log.2023-05-16_11')
data_true_b = load_robot_allocator_log_file(
    'curr/robot_allocator.log.2023-05-16_12')
data_true_c = load_robot_allocator_log_file(
    'curr/robot_allocator.log.2023-05-16_13')

print(len(data_true_a), len(data_true_b), len(data_true_c), len(data_true_d))
data_true = np.concatenate([data_true_a, data_true_b, data_true_c, data_true_d], axis=0)
print(len(data_true))
plt.figure(figsize=(8, 6))
# plt.hist(data_euclid, bins=40, alpha=0.5, label='Euclidean Heuristic')
plt.hist(data_true, bins=80, alpha=1.0, label='True Heuristic', log=True)
plt.xlabel('Processing Time (ms)')
plt.ylabel('Frequency (count)')
plt.title(f'generate_path histogram over {len(data_true)} entries')
# plt.title('Comparing Euclidean vs True Heuristic Functions')

min_ylim, max_ylim = plt.ylim()
# plt.axvline(data_euclid.mean(), color='blue', linestyle='dashed')
# plt.text(data_euclid.mean(), max_ylim*0.9,
#          f' Euclid-H Mean - {data_euclid.mean():.2f} ms', fontsize=6)
plt.axvline(data_true.mean(), color='orange', linestyle='dashed')
plt.text(data_true.mean(), max_ylim*0.8,
         f' True-H Mean - {data_true.mean():.2f} ms', fontsize=6)
min_ylim, max_ylim = plt.ylim()
plt.legend()
plt.tight_layout()
plt.show()
