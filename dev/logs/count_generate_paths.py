import numpy as np
import matplotlib.pyplot as plt  # type: ignore


def load_robot_allocator_log_file(filename) -> list[dict]:
    # Expect to run everything locally within this directory
    data = []
    with open(filename, 'r', encoding='utf8') as file:
        for line in file:
            parts = line.split(' - ')
            if not ('generate_path' in parts[3]):
                continue

            # example message contains 'generate_path took 0.387 ms'
            _, _, duration_ms_str, _ = parts[3].split(' ')
            data.append(float(duration_ms_str))
    return np.array(data)


print('Loading data')
data_euclid = load_robot_allocator_log_file(
    'curr/TEST1_robot_allocator_EUCLIDEAN.log')
data_true = load_robot_allocator_log_file(
    'curr\TEST2_robot_allocator_TRUE.log')
# print(data)


plt.figure(figsize=(6, 4))
# plt.subplot(121)
plt.hist(data_euclid, bins=40, alpha=0.5, label='Euclidean Heuristic')
plt.hist(data_true, bins=40, alpha=0.5, label='True Heuristic')
plt.xlabel('Processing Time (ms)')
plt.ylabel('Frequency (count)')
plt.title('Comparing Euclidean vs True Heuristic Functions')

min_ylim, max_ylim = plt.ylim()
plt.axvline(data_euclid.mean(), color='blue', linestyle='dashed')
plt.text(data_euclid.mean(), max_ylim*0.9,
         f' Euclid-H Mean - {data_euclid.mean():.2f} ms', fontsize=6)
plt.axvline(data_true.mean(), color='orange', linestyle='dashed')
plt.text(data_true.mean(), max_ylim*0.8,
         f' True-H Mean - {data_true.mean():.2f} ms', fontsize=6)
min_ylim, max_ylim = plt.ylim()
plt.legend()
plt.tight_layout()
plt.show()
