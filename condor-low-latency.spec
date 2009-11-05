%{!?is_fedora: %define is_fedora %(/bin/sh -c "if [ -e /etc/fedora-release ];then echo '1'; fi")}
%define rel 21

Summary: Low Latency Scheduling
Name: condor-low-latency
Version: 1.0
Release: %{rel}%{?dist}
License: ASL 2.0
Group: Applications/System
URL: http://www.redhat.com/mrg
# This is a Red Hat maintained package which is specific to
# our distribution.  Thus the source is only available from
# within this srpm.
Source0: %{name}-%{version}-%{rel}.tar.gz
BuildRoot: %(mktemp -ud %{_tmppath}/%{name}-%{version}-%{release}-XXXXXX)
BuildArch: noarch
Requires: python >= 2.3
Requires: condor >= 7.0.2-4
Requires: condor-job-hooks
Requires: python-condor-job-hooks-common
Requires: python-qpid

%description
Low Latency Scheduling provides a means for bypassing condor's normal
scheduling process and instead submit work directly to an execute node
using the AMQP protocol.

%prep
%setup -q

%build

%install
rm -rf %{buildroot}
mkdir -p %{buildroot}%{_sbindir}
mkdir -p %{buildroot}/%{_sysconfdir}/condor
cp -f carod %{buildroot}/%_sbindir
cp -f config/carod.conf %{buildroot}/%{_sysconfdir}/condor

%post
%if 0%{?is_fedora} == 0
if [[ -f /etc/opt/grid/carod.conf ]]; then
   mv -f /etc/opt/grid/carod.conf /etc/condor
   rmdir --ignore-fail-on-non-empty -p /etc/opt/grid
fi
%endif
exit 0

%clean
rm -rf %{buildroot}

%files
%defattr(-,root,root,-)
%doc LICENSE-2.0.txt INSTALL
%config(noreplace) %_sysconfdir/condor/carod.conf
%defattr(0755,root,root,-)
%_sbindir/carod

%changelog
* Fri Oct 23 2009  <rrati@redhat> - 1.0-21
- Removed conflict with condor-ec2-enhanced

* Tue Oct 15 2009  <rrati@redhat> - 1.0-20
- Removed error message when processng a status update that would be printed
  if carod received an update for a job it didn't know about

* Tue Aug 18 2009  <rrati@redhat> - 1.0-19
- Split documentation into two files, one for carod and one for
  the job-hooks
- Added conflict with condor-ec2-enhanced
- Removed ll_condor_config and pulled its contents into the INSTALL
  documentation

* Mon Aug 17 2009  <rrati@redhat> - 1.0-18
- Handle AMQP broker restarts (BZ488998)
- Fixed typo that allows correct usage of --help (BZ491826)

* Mon Jul 27 2009  <rrati@redhat> - 1.0-17
- Clean up buildroot in install section

* Mon Jul 27 2009  <rrati@redhat> - 1.0-16
- Updated dependencies to match hooks-common rename

* Mon Jul 27 2009  <rrati@redhat> - 1.0-15
- Fix rpmlint/packaging issues

* Wed Jun 24 2009  <rrati@redhat> - 1.0-14
- carod will first look for its configuration in condor's configuration
  files, then fall back to its config file
- The config file has moved from /etc/opt/grid to /etc/condor
- Condor should control the start/stop/restart of carod
 
* Tue Jun  2 2009  <rrati@redhat> - 1.0-13
- The correlation id on response messages is set to the message id of the job
  running

* Fri Mar 13 2009  <rrati@redhat> - 1.0-12
- Fixed deadlocking issues (BZ489874)
- Fixed problems sending results message (BZ489880)
- Fixed exception cases that would result in the message not getting
  released for reprocessing

* Fri Mar  6 2009  <rrati@redhat> - 1.0-11
- Removed the vanilla universe restriction (BZ489001)
- Fixed issue with AMQP message body of None (BZ489000)
- Fxed equal sign (=) in attribute value ending up part of the header
- Attributes and values are trimmed (BZ489003)
- Preserve attribute value type information (BZ488996)
 
* Thu Feb 19 2009  <rrati@redhat> - 1.0-10
- Set JobStatus correctly (BZ459615)

* Fri Feb 13 2009  <rrati@redhat> - 1.0-9
- Change source tarball name

* Thu Jan 29 2009  <rrati@redhat> - 1.0-8
- Fix init file patch for Red Hat Enterprise Linux 4

* Mon Jan 12 2009  <rrati@redhat> - 1.0-7
- BZ474405

* Tue Dec 16 2008  <rrati@redhat> - 1.0-6
- If TransferOutput is set, only transfer the files listed as well as
  stdout/stderr files if they exist
- Only package files in the job's iwd

* Fri Dec  5 2008  <rrati@redhat> - 1.0-5
- Cleaned up socket close code to provide cleaner shutdown

* Wed Dec  3 2008  <rrati@redhat> - 1.0-4
- Fixed python dependency with RHEL4
- Fixed issues running on python 2.3

* Wed Nov 19 2008  <rrati@redhat> - 1.0-3
- Low Latency daemon is on by default
- Daemon now appropriately handles Universe being set

* Fri Nov  4 2008  <rrati@redhat> - 1.0-2
- Add changelog
- Fix rpmlint issues
- Renamed init script to condor-low-latency

* Fri Nov  4 2008  <rrati@redhat> - 1.0-1
- Initial packaging

