import os
import popen2

from independent_jobs.engines.BatchClusterComputationEngine import BatchClusterComputationEngine
from independent_jobs.tools.Log import logger
from independent_jobs.tools.Time import Time


class SlurmComputationEngine(BatchClusterComputationEngine):
    def __init__(self, batch_parameters, check_interval=10, do_clean_up=False):
        BatchClusterComputationEngine.__init__(self,
                                               batch_parameters=batch_parameters,
                                               check_interval=check_interval,
                                               submission_cmd="sbatch",
                                               do_clean_up=do_clean_up,
                                               submission_delay=0.01,
                                               max_jobs_in_queue=2000)
        
        # automatically set queue if not specified by user
        try:
            self.batch_parameters.qos
        except AttributeError:
            self.batch_parameters.qos = self._infer_slurm_qos(batch_parameters.max_walltime,
                                                              batch_parameters.nodes)

    def _infer_slurm_qos(self, max_walltime, nodes):
        if max_walltime <= 60 * 60 and \
           nodes <= 90:
            qos = "short"
        elif max_walltime <= 60 * 60 * 24 and \
             nodes <= 70:
            qos = "normal"
        elif max_walltime <= 60 * 60 * 72 and \
             nodes <= 20:
            qos = "medium"
        elif max_walltime <= 60 * 60 * 24 and \
             nodes <= 10:
            qos = "long"
        else:
            logger.warning("Unable to infer slurm qos. Setting to normal")
            qos = "normal"
            
        return qos

    def create_batch_script(self, job_name, dispatcher_string):
        command = "nice -n 10 " + dispatcher_string
       # precommand = "export PYHTONPATH=$PYTHONPATH:/nfs/nhome/live/vincenta/git/independent-jobs/"
        precommand = "export PYTHONPATH=$PYTHONPATH:/nfs/nhome/live/jmagraner/gatsby-hackathon-seizure/code/python/"
	days, hours, minutes, seconds = Time.sec_to_all(self.batch_parameters.max_walltime)
        walltime = '%d-%d:%d:%d' % (days, hours, minutes, seconds)
        
        num_nodes = str(self.batch_parameters.nodes)
        # note memory is in megabyes
        memory = str(self.batch_parameters.memory)
        workdir = self.get_job_foldername(job_name)

        output = workdir + os.sep + BatchClusterComputationEngine.output_filename
        error = workdir + os.sep + BatchClusterComputationEngine.error_filename
        
        job_string = """#!/bin/bash
#SBATCH -J %s
#SBATCH --time=%s
#SBATCH --qos=%s
#SBATCH -n %s
#SBATCH --mem=%s
#SBATCH --output=%s
#SBATCH --error=%s
cd %s
%s
%s""" % (job_name, walltime, self.batch_parameters.qos, num_nodes, memory, output, error, workdir,precommand
         ,command)
        
        return job_string

    def submit_to_batch_system(self, job_string):
        # send job_string to batch command
        outpipe, inpipe = popen2.popen2(self.submission_cmd)
        inpipe.write(job_string + os.linesep)
        inpipe.close()
        
        job_id = outpipe.read().strip().split(" ")[-1]
        outpipe.close()
        
        return job_id