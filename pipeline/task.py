import luigi

class TaskName(luigi.Task):

    def requires(self):
        """ This must return any tasks that this task depends upon
        """
        return []

    def output(self):
        """ Returns the location of the output files of this task.
        """
        return [luigi.LocalTarget("output file")]

    def run(self):
        """ Execute the task.
        """
        pass

