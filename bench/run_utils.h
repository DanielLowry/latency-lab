#pragma once

#include "cli.h"
#include "registry.h"

#include <string>

const Case* resolve_case(const std::string& name);
std::string resolve_output_path(const CliOptions& options);
std::string resolve_meta_path(const CliOptions& options);
std::string resolve_stdout_path(const CliOptions& options);
