FROM mcr.microsoft.com/dotnet/sdk:8.0

WORKDIR /runner/App

COPY App.csproj /runner/App/App.csproj

ENV DOTNET_CLI_TELEMETRY_OPTOUT=1 \
    DOTNET_NOLOGO=1 \
    DOTNET_SKIP_FIRST_TIME_EXPERIENCE=1 \
    NUGET_PACKAGES=/tmp/nuget \
    DOTNET_CLI_HOME=/tmp/dotnet \
    HOME=/tmp \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

CMD ["/bin/sh", "-lc", "dotnet build /runner/App/App.csproj --nologo --verbosity quiet --configuration Release --output /tmp/out --property:UseSharedCompilation=false --property:BaseIntermediateOutputPath=/tmp/obj/ --property:IntermediateOutputPath=/tmp/obj/ --property:MSBuildProjectExtensionsPath=/tmp/obj/ --property:RestorePackagesPath=/tmp/nuget/ >/tmp/build_stdout.log 2>/tmp/build_stderr.log || { cat /tmp/build_stdout.log; cat /tmp/build_stderr.log 1>&2; exit 1; }; dotnet /tmp/out/App.dll"]
