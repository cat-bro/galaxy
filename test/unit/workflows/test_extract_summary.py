import unittest

from galaxy import model
from galaxy.workflow import extract

UNDEFINED_JOB = object()


class TestWorkflowExtractSummary(unittest.TestCase):

    def setUp(self):
        self.history = MockHistory()
        self.trans = MockTrans(self.history)

    def test_empty_history(self):
        job_dict, warnings = extract.summarize(trans=self.trans)
        assert not warnings
        assert not job_dict

    def test_summarize_returns_name_and_dataset_list(self):
        # Create two jobs and three datasets, test they are groupped
        # by job correctly with correct output names.
        hda1 = MockHda()
        self.history.active_datasets.append(hda1)
        hda2 = MockHda(job=hda1.job, output_name="out2")
        self.history.active_datasets.append(hda2)
        hda3 = MockHda(output_name="out3")
        self.history.active_datasets.append(hda3)

        job_dict, warnings = extract.summarize(trans=self.trans)
        assert len(job_dict) == 2
        assert not warnings
        self.assertEquals(job_dict[hda1.job], [('out1', hda1), ('out2', hda2)])
        self.assertEquals(job_dict[hda3.job], [('out3', hda3)])

    def test_finds_original_job_if_copied(self):
        hda = MockHda()
        derived_hda_1 = MockHda()
        derived_hda_1.copied_from_history_dataset_association = hda
        derived_hda_2 = MockHda()
        derived_hda_2.copied_from_history_dataset_association = derived_hda_1
        self.history.active_datasets.append(derived_hda_2)
        job_dict, warnings = extract.summarize(trans=self.trans)
        assert not warnings
        assert len(job_dict) == 1
        self.assertEquals(job_dict[hda.job], [('out1', derived_hda_2)])

    def test_fake_job_hda(self):
        """ Fakes job if creating_job_associations is empty.
        """
        hda = MockHda(job=UNDEFINED_JOB)
        self.history.active_datasets.append(hda)
        job_dict, warnings = extract.summarize(trans=self.trans)
        assert not warnings
        assert len(job_dict) == 1
        fake_job = job_dict.keys()[0]
        assert fake_job.id.startswith("fake_")
        datasets = list(job_dict.values())[0]
        assert datasets == [(None, hda)]

    def test_fake_job_hdca(self):
        hdca = MockHdca()
        self.history.active_datasets.append(hdca)
        job_dict, warnings = extract.summarize(trans=self.trans)
        assert not warnings
        assert len(job_dict) == 1
        fake_job = job_dict.keys()[0]
        assert fake_job.id.startswith("fake_")
        assert fake_job.is_fake
        content_instances = next(iter(job_dict.values()))
        assert content_instances == [(None, hdca)]

    def test_implicit_map_job_hdca(self):
        creating_job = model.Job()
        hdca = MockHdca(implicit_output_name="out1", job=creating_job)
        self.history.active_datasets.append(hdca)
        job_dict, warnings = extract.summarize(trans=self.trans)
        assert not warnings
        assert len(job_dict) == 1
        job = job_dict.keys()[0]
        assert job is creating_job

    def test_warns_and_skips_datasets_if_not_finished(self):
        hda = MockHda(state='queued')
        self.history.active_datasets.append(hda)
        job_dict, warnings = extract.summarize(trans=self.trans)
        assert warnings
        assert len(job_dict) == 0


class MockHistory(object):

    def __init__(self):
        self.active_datasets = []

    @property
    def active_contents(self):
        return self.active_datasets


class MockTrans(object):

    def __init__(self, history):
        self.history = history

    def get_history(self):
        return self.history


class MockHda(object):

    def __init__(self, state='ok', output_name='out1', job=None):
        self.id = 123
        self.state = state
        self.copied_from_history_dataset_association = None
        self.history_content_type = "dataset"
        if job is not UNDEFINED_JOB:
            if not job:
                job = model.Job()
            self.job = job
            assoc = model.JobToOutputDatasetAssociation(output_name, self)
            assoc.job = job
            self.creating_job_associations = [assoc]
        else:
            self.creating_job_associations = []


class MockHdca(object):

    def __init__(self, implicit_output_name=None, job=None, hid=1):
        self.id = 124
        self.copied_from_history_dataset_collection_association = None
        self.history_content_type = "dataset_collection"
        self.implicit_output_name = implicit_output_name
        self.hid = 1
        self.collection = model.DatasetCollection()
        self.creating_job_associations = []
        element = model.DatasetCollectionElement(
            collection=self.collection,
            element=model.HistoryDatasetAssociation(),
            element_index=0,
            element_identifier="moocow",
        )
        element.dataset_instance.dataset = model.Dataset()
        element.dataset_instance.dataset.state = "ok"
        creating = model.JobToOutputDatasetAssociation(
            implicit_output_name,
            element.dataset_instance,
        )
        creating.job = job
        element.dataset_instance.creating_job_associations = [
            creating,
        ]
        self.collection.elements = [element]
