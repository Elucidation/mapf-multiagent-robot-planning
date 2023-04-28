FROM ubuntu:20.04

# Load dependencies
RUN apt-get update && DEBIAN_FRONTEND=noninteractive TZ=America/Los_Angeles apt-get install -y python3.9 python3.9-distutils curl && apt-get clean && rm -rf /var/lib/apt/lists/* && curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py && python3.9 get-pip.py && rm get-pip.py


COPY requirements.txt .

RUN pip install -r requirements.txt

# Install pip requirements
#RUN pip install --no-cache-dir -r /home/app/mapf-multiagent-robot-planning/requirements.txt

# WORKDIR /home/app/mapf-multiagent-robot-planning/dev/


# CMD ["python3.9", "-m", "unittest"] 

CMD ["/bin/bash"]