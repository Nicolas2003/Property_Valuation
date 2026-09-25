FROM jenkins/jenkins:lts
USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
      python3 python3-venv python3-pip ruby-full build-essential openssh-client \
    && rm -rf /var/lib/apt/lists/* \
    && gem install kamal
USER jenkins
RUN jenkins-plugin-cli --plugins workflow-aggregator git