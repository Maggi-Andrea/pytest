import pytest
from _pytest._code.code import ExceptionChainRepr
from _pytest.pathlib import Path
from _pytest.reports import CollectReport
from _pytest.reports import TestReport


class TestReportSerialization:
    def test_xdist_longrepr_to_str_issue_241(self, testdir):
        """
        Regarding issue pytest-xdist#241

        This test came originally from test_remote.py in xdist (ca03269).
        """
        testdir.makepyfile(
            """
            def test_a(): assert False
            def test_b(): pass
        """
        )
        reprec = testdir.inline_run()
        reports = reprec.getreports("pytest_runtest_logreport")
        assert len(reports) == 6
        test_a_call = reports[1]
        assert test_a_call.when == "call"
        assert test_a_call.outcome == "failed"
        assert test_a_call._to_json()["longrepr"]["reprtraceback"]["style"] == "long"
        test_b_call = reports[4]
        assert test_b_call.when == "call"
        assert test_b_call.outcome == "passed"
        assert test_b_call._to_json()["longrepr"] is None

    def test_xdist_report_longrepr_reprcrash_130(self, testdir):
        """Regarding issue pytest-xdist#130

        This test came originally from test_remote.py in xdist (ca03269).
        """
        reprec = testdir.inline_runsource(
            """
                    def test_fail():
                        assert False, 'Expected Message'
                """
        )
        reports = reprec.getreports("pytest_runtest_logreport")
        assert len(reports) == 3
        rep = reports[1]
        added_section = ("Failure Metadata", "metadata metadata", "*")
        rep.longrepr.sections.append(added_section)
        d = rep._to_json()
        a = TestReport._from_json(d)
        # Check assembled == rep
        assert a.__dict__.keys() == rep.__dict__.keys()
        for key in rep.__dict__.keys():
            if key != "longrepr":
                assert getattr(a, key) == getattr(rep, key)
        assert rep.longrepr.reprcrash.lineno == a.longrepr.reprcrash.lineno
        assert rep.longrepr.reprcrash.message == a.longrepr.reprcrash.message
        assert rep.longrepr.reprcrash.path == a.longrepr.reprcrash.path
        assert rep.longrepr.reprtraceback.entrysep == a.longrepr.reprtraceback.entrysep
        assert (
            rep.longrepr.reprtraceback.extraline == a.longrepr.reprtraceback.extraline
        )
        assert rep.longrepr.reprtraceback.style == a.longrepr.reprtraceback.style
        assert rep.longrepr.sections == a.longrepr.sections
        # Missing section attribute PR171
        assert added_section in a.longrepr.sections

    def test_reprentries_serialization_170(self, testdir):
        """Regarding issue pytest-xdist#170

        This test came originally from test_remote.py in xdist (ca03269).
        """
        from _pytest._code.code import ReprEntry

        reprec = testdir.inline_runsource(
            """
                            def test_repr_entry():
                                x = 0
                                assert x
                        """,
            "--showlocals",
        )
        reports = reprec.getreports("pytest_runtest_logreport")
        assert len(reports) == 3
        rep = reports[1]
        d = rep._to_json()
        a = TestReport._from_json(d)

        rep_entries = rep.longrepr.reprtraceback.reprentries
        a_entries = a.longrepr.reprtraceback.reprentries
        for i in range(len(a_entries)):
            assert isinstance(rep_entries[i], ReprEntry)
            assert rep_entries[i].lines == a_entries[i].lines
            assert rep_entries[i].reprfileloc.lineno == a_entries[i].reprfileloc.lineno
            assert (
                rep_entries[i].reprfileloc.message == a_entries[i].reprfileloc.message
            )
            assert rep_entries[i].reprfileloc.path == a_entries[i].reprfileloc.path
            assert rep_entries[i].reprfuncargs.args == a_entries[i].reprfuncargs.args
            assert rep_entries[i].reprlocals.lines == a_entries[i].reprlocals.lines
            assert rep_entries[i].style == a_entries[i].style

    def test_reprentries_serialization_196(self, testdir):
        """Regarding issue pytest-xdist#196

        This test came originally from test_remote.py in xdist (ca03269).
        """
        from _pytest._code.code import ReprEntryNative

        reprec = testdir.inline_runsource(
            """
                            def test_repr_entry_native():
                                x = 0
                                assert x
                        """,
            "--tb=native",
        )
        reports = reprec.getreports("pytest_runtest_logreport")
        assert len(reports) == 3
        rep = reports[1]
        d = rep._to_json()
        a = TestReport._from_json(d)

        rep_entries = rep.longrepr.reprtraceback.reprentries
        a_entries = a.longrepr.reprtraceback.reprentries
        for i in range(len(a_entries)):
            assert isinstance(rep_entries[i], ReprEntryNative)
            assert rep_entries[i].lines == a_entries[i].lines

    def test_itemreport_outcomes(self, testdir):
        """
        This test came originally from test_remote.py in xdist (ca03269).
        """
        reprec = testdir.inline_runsource(
            """
            import pytest
            def test_pass(): pass
            def test_fail(): 0/0
            @pytest.mark.skipif("True")
            def test_skip(): pass
            def test_skip_imperative():
                pytest.skip("hello")
            @pytest.mark.xfail("True")
            def test_xfail(): 0/0
            def test_xfail_imperative():
                pytest.xfail("hello")
        """
        )
        reports = reprec.getreports("pytest_runtest_logreport")
        assert len(reports) == 17  # with setup/teardown "passed" reports
        for rep in reports:
            d = rep._to_json()
            newrep = TestReport._from_json(d)
            assert newrep.passed == rep.passed
            assert newrep.failed == rep.failed
            assert newrep.skipped == rep.skipped
            if newrep.skipped and not hasattr(newrep, "wasxfail"):
                assert len(newrep.longrepr) == 3
            assert newrep.outcome == rep.outcome
            assert newrep.when == rep.when
            assert newrep.keywords == rep.keywords
            if rep.failed:
                assert newrep.longreprtext == rep.longreprtext

    def test_collectreport_passed(self, testdir):
        """This test came originally from test_remote.py in xdist (ca03269)."""
        reprec = testdir.inline_runsource("def test_func(): pass")
        reports = reprec.getreports("pytest_collectreport")
        for rep in reports:
            d = rep._to_json()
            newrep = CollectReport._from_json(d)
            assert newrep.passed == rep.passed
            assert newrep.failed == rep.failed
            assert newrep.skipped == rep.skipped

    def test_collectreport_fail(self, testdir):
        """This test came originally from test_remote.py in xdist (ca03269)."""
        reprec = testdir.inline_runsource("qwe abc")
        reports = reprec.getreports("pytest_collectreport")
        assert reports
        for rep in reports:
            d = rep._to_json()
            newrep = CollectReport._from_json(d)
            assert newrep.passed == rep.passed
            assert newrep.failed == rep.failed
            assert newrep.skipped == rep.skipped
            if rep.failed:
                assert newrep.longrepr == str(rep.longrepr)

    def test_extended_report_deserialization(self, testdir):
        """This test came originally from test_remote.py in xdist (ca03269)."""
        reprec = testdir.inline_runsource("qwe abc")
        reports = reprec.getreports("pytest_collectreport")
        assert reports
        for rep in reports:
            rep.extra = True
            d = rep._to_json()
            newrep = CollectReport._from_json(d)
            assert newrep.extra
            assert newrep.passed == rep.passed
            assert newrep.failed == rep.failed
            assert newrep.skipped == rep.skipped
            if rep.failed:
                assert newrep.longrepr == str(rep.longrepr)

    def test_paths_support(self, testdir):
        """Report attributes which are py.path or pathlib objects should become strings."""
        testdir.makepyfile(
            """
            def test_a():
                assert False
        """
        )
        reprec = testdir.inline_run()
        reports = reprec.getreports("pytest_runtest_logreport")
        assert len(reports) == 3
        test_a_call = reports[1]
        test_a_call.path1 = testdir.tmpdir
        test_a_call.path2 = Path(testdir.tmpdir)
        data = test_a_call._to_json()
        assert data["path1"] == str(testdir.tmpdir)
        assert data["path2"] == str(testdir.tmpdir)

    def test_deserialization_failure(self, testdir):
        """Check handling of failure during deserialization of report types."""
        testdir.makepyfile(
            """
            def test_a():
                assert False
        """
        )
        reprec = testdir.inline_run()
        reports = reprec.getreports("pytest_runtest_logreport")
        assert len(reports) == 3
        test_a_call = reports[1]
        data = test_a_call._to_json()
        entry = data["longrepr"]["reprtraceback"]["reprentries"][0]
        assert entry["type"] == "ReprEntry"

        entry["type"] = "Unknown"
        with pytest.raises(
            RuntimeError, match="INTERNALERROR: Unknown entry type returned: Unknown"
        ):
            TestReport._from_json(data)

    @pytest.mark.parametrize("report_class", [TestReport, CollectReport])
    def test_chained_exceptions(self, testdir, tw_mock, report_class):
        """Check serialization/deserialization of report objects containing chained exceptions (#5786)"""
        testdir.makepyfile(
            """
            def foo():
                raise ValueError('value error')
            def test_a():
                try:
                    foo()
                except ValueError as e:
                    raise RuntimeError('runtime error') from e
            if {error_during_import}:
                test_a()
        """.format(
                error_during_import=report_class is CollectReport
            )
        )

        reprec = testdir.inline_run()
        if report_class is TestReport:
            reports = reprec.getreports("pytest_runtest_logreport")
            # we have 3 reports: setup/call/teardown
            assert len(reports) == 3
            # get the call report
            report = reports[1]
        else:
            assert report_class is CollectReport
            # two collection reports: session and test file
            reports = reprec.getreports("pytest_collectreport")
            assert len(reports) == 2
            report = reports[1]

        def check_longrepr(longrepr):
            """Check the attributes of the given longrepr object according to the test file.

            We can get away with testing both CollectReport and TestReport with this function because
            the longrepr objects are very similar.
            """
            assert isinstance(longrepr, ExceptionChainRepr)
            assert longrepr.sections == [("title", "contents", "=")]
            assert len(longrepr.chain) == 2
            entry1, entry2 = longrepr.chain
            tb1, fileloc1, desc1 = entry1
            tb2, fileloc2, desc2 = entry2

            assert "ValueError('value error')" in str(tb1)
            assert "RuntimeError('runtime error')" in str(tb2)

            assert (
                desc1
                == "The above exception was the direct cause of the following exception:"
            )
            assert desc2 is None

        assert report.failed
        assert len(report.sections) == 0
        report.longrepr.addsection("title", "contents", "=")
        check_longrepr(report.longrepr)

        data = report._to_json()
        loaded_report = report_class._from_json(data)

        assert loaded_report.failed
        check_longrepr(loaded_report.longrepr)

        # make sure we don't blow up on ``toterminal`` call; we don't test the actual output because it is very
        # brittle and hard to maintain, but we can assume it is correct because ``toterminal`` is already tested
        # elsewhere and we do check the contents of the longrepr object after loading it.
        loaded_report.longrepr.toterminal(tw_mock)

    def test_chained_exceptions_no_reprcrash(
        self, testdir, tw_mock,
    ):
        """Regression test for tracebacks without a reprcrash (#5971)

        This happens notably on exceptions raised by multiprocess.pool: the exception transfer
        from subprocess to main process creates an artificial exception, which ExceptionInfo
        can't obtain the ReprFileLocation from.
        """
        testdir.makepyfile(
            """
            from concurrent.futures import ProcessPoolExecutor

            def func():
                raise ValueError('value error')

            def test_a():
                with ProcessPoolExecutor() as p:
                    p.submit(func).result()
        """
        )
        reprec = testdir.inline_run()

        reports = reprec.getreports("pytest_runtest_logreport")

        def check_longrepr(longrepr):
            assert isinstance(longrepr, ExceptionChainRepr)
            assert len(longrepr.chain) == 2
            entry1, entry2 = longrepr.chain
            tb1, fileloc1, desc1 = entry1
            tb2, fileloc2, desc2 = entry2

            assert "RemoteTraceback" in str(tb1)
            assert "ValueError: value error" in str(tb2)

            assert fileloc1 is None
            assert fileloc2.message == "ValueError: value error"

        # 3 reports: setup/call/teardown: get the call report
        assert len(reports) == 3
        report = reports[1]

        assert report.failed
        check_longrepr(report.longrepr)

        data = report._to_json()
        loaded_report = TestReport._from_json(data)

        assert loaded_report.failed
        check_longrepr(loaded_report.longrepr)

        # for same reasons as previous test, ensure we don't blow up here
        loaded_report.longrepr.toterminal(tw_mock)


class TestHooks:
    """Test that the hooks are working correctly for plugins"""

    def test_test_report(self, testdir, pytestconfig):
        testdir.makepyfile(
            """
            def test_a(): assert False
            def test_b(): pass
        """
        )
        reprec = testdir.inline_run()
        reports = reprec.getreports("pytest_runtest_logreport")
        assert len(reports) == 6
        for rep in reports:
            data = pytestconfig.hook.pytest_report_to_serializable(
                config=pytestconfig, report=rep
            )
            assert data["$report_type"] == "TestReport"
            new_rep = pytestconfig.hook.pytest_report_from_serializable(
                config=pytestconfig, data=data
            )
            assert new_rep.nodeid == rep.nodeid
            assert new_rep.when == rep.when
            assert new_rep.outcome == rep.outcome

    def test_collect_report(self, testdir, pytestconfig):
        testdir.makepyfile(
            """
            def test_a(): assert False
            def test_b(): pass
        """
        )
        reprec = testdir.inline_run()
        reports = reprec.getreports("pytest_collectreport")
        assert len(reports) == 2
        for rep in reports:
            data = pytestconfig.hook.pytest_report_to_serializable(
                config=pytestconfig, report=rep
            )
            assert data["$report_type"] == "CollectReport"
            new_rep = pytestconfig.hook.pytest_report_from_serializable(
                config=pytestconfig, data=data
            )
            assert new_rep.nodeid == rep.nodeid
            assert new_rep.when == "collect"
            assert new_rep.outcome == rep.outcome

    @pytest.mark.parametrize(
        "hook_name", ["pytest_runtest_logreport", "pytest_collectreport"]
    )
    def test_invalid_report_types(self, testdir, pytestconfig, hook_name):
        testdir.makepyfile(
            """
            def test_a(): pass
            """
        )
        reprec = testdir.inline_run()
        reports = reprec.getreports(hook_name)
        assert reports
        rep = reports[0]
        data = pytestconfig.hook.pytest_report_to_serializable(
            config=pytestconfig, report=rep
        )
        data["$report_type"] = "Unknown"
        with pytest.raises(AssertionError):
            _ = pytestconfig.hook.pytest_report_from_serializable(
                config=pytestconfig, data=data
            )
