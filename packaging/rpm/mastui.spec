Name:           mastui
Version:        %{_version}
Release:        1%{?dist}
Summary:        A Mastodon TUI client
License:        MIT
URL:            https://github.com/kimusan/mastui
BuildArch:      x86_64

# Turn off debuginfo package generation since this is a pre-compiled binary
%global debug_package %{nil}

%description
A Textual-based terminal user interface client for Mastodon.

%install
mkdir -p %{buildroot}%{_bindir}
mkdir -p %{buildroot}%{_datadir}/applications
mkdir -p %{buildroot}%{_datadir}/icons/hicolor/512x512/apps
mkdir -p %{buildroot}%{_datadir}/licenses/%{name}

install -m 755 %{_sourcedir}/mastui %{buildroot}%{_bindir}/mastui
install -m 644 %{_sourcedir}/mastui.desktop %{buildroot}%{_datadir}/applications/mastui.desktop
install -m 644 %{_sourcedir}/mastui.png %{buildroot}%{_datadir}/icons/hicolor/512x512/apps/mastui.png
if [ -f %{_sourcedir}/LICENSE ]; then
    install -m 644 %{_sourcedir}/LICENSE %{buildroot}%{_datadir}/licenses/%{name}/LICENSE
fi

%files
%{_bindir}/mastui
%{_datadir}/applications/mastui.desktop
%{_datadir}/icons/hicolor/512x512/apps/mastui.png
%license %{_datadir}/licenses/%{name}/LICENSE
