package main

import (
	"context"
	"errors"
	"flag"
	"fmt"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"slices"
	"strings"
	"syscall"
	"time"

	"github.com/mark3labs/mcp-go/server"

	mcpcmdzero "github.com/cmdzero/cmdzero-public-api-mcp"
	"github.com/cmdzero/cmdzero-public-api-mcp/tools"
)

type disabledTools struct {
	enabledTools string

	health, organizations, applications, users,
	investigations, remediations, businessContext,
	catalog bool
}

func (dt *disabledTools) addFlags() {
	flag.StringVar(&dt.enabledTools, "enabled-tools",
		"health,organizations,applications,users,investigations,remediations,businessContext,catalog",
		"Comma-separated list of enabled tool categories")

	flag.BoolVar(&dt.health, "disable-health", false, "Disable health tools")
	flag.BoolVar(&dt.organizations, "disable-organizations", false, "Disable organization tools")
	flag.BoolVar(&dt.applications, "disable-applications", false, "Disable application tools")
	flag.BoolVar(&dt.users, "disable-users", false, "Disable user tools")
	flag.BoolVar(&dt.investigations, "disable-investigations", false, "Disable investigation tools")
	flag.BoolVar(&dt.remediations, "disable-remediations", false, "Disable remediation tools")
	flag.BoolVar(&dt.businessContext, "disable-business-context", false, "Disable business context tools")
	flag.BoolVar(&dt.catalog, "disable-catalog", false, "Disable catalog tools")
}

func maybeAddTools(s *server.MCPServer, tf func(*server.MCPServer), enabledTools []string, disable bool, category string) {
	if !slices.Contains(enabledTools, category) {
		slog.Debug("Not enabling tools", "category", category)
		return
	}
	if disable {
		slog.Info("Disabling tools", "category", category)
		return
	}
	slog.Debug("Enabling tools", "category", category)
	tf(s)
}

func (dt *disabledTools) addTools(s *server.MCPServer) {
	enabled := strings.Split(dt.enabledTools, ",")
	maybeAddTools(s, tools.AddHealthTools, enabled, dt.health, "health")
	maybeAddTools(s, tools.AddOrganizationTools, enabled, dt.organizations, "organizations")
	maybeAddTools(s, tools.AddApplicationTools, enabled, dt.applications, "applications")
	maybeAddTools(s, tools.AddUserTools, enabled, dt.users, "users")
	maybeAddTools(s, tools.AddInvestigationTools, enabled, dt.investigations, "investigations")
	maybeAddTools(s, tools.AddRemediationTools, enabled, dt.remediations, "remediations")
	maybeAddTools(s, tools.AddBusinessContextTools, enabled, dt.businessContext, "businessContext")
	maybeAddTools(s, tools.AddCatalogTools, enabled, dt.catalog, "catalog")
}

func newServer(dt disabledTools) *server.MCPServer {
	s := server.NewMCPServer("cmdzero-public-api-mcp", mcpcmdzero.Version(), server.WithInstructions(`
This server provides tools for interacting with the Command Zero Public API —
an automated security investigation platform.

Available capabilities:
- Health: Verify API connectivity and authentication.
- Organizations: List organizations accessible to your application.
- Applications: List and retrieve API applications in your organization.
- Users: List and retrieve users for assignment and collaboration.
- Investigations: Start investigations from alerts or templates, list/query/get investigations,
  update status, assign analysts, and close investigations with verdicts.
- Remediations: Browse remediation templates, execute remediation actions against subjects
  (disable users, revoke sessions, etc.), and monitor execution status.
- Business Context: Upload and manage contextual information about subjects to enrich investigations.
- Catalog: Browse catalog types that define alert schemas and data structures.

Key workflows:
1. Receive alert → start investigation → monitor progress → assign analyst → review findings → close
2. Investigation completes → execute remediation (disable user, revoke access) → verify success
3. Upload business context → enrich future investigations with organizational knowledge
`))
	dt.addTools(s)
	return s
}

func runHTTPServer(ctx context.Context, srv interface {
	Start(string) error
	Shutdown(context.Context) error
}, addr, transportName string) error {
	serverErr := make(chan error, 1)
	go func() {
		if err := srv.Start(addr); err != nil {
			serverErr <- err
		}
		close(serverErr)
	}()

	select {
	case err := <-serverErr:
		return err
	case <-ctx.Done():
		slog.Info(fmt.Sprintf("%s server shutting down...", transportName))
		shutdownCtx, shutdownCancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer shutdownCancel()
		if err := srv.Shutdown(shutdownCtx); err != nil {
			return fmt.Errorf("shutdown error: %v", err)
		}
		select {
		case err := <-serverErr:
			if err != nil && !errors.Is(err, http.ErrServerClosed) {
				return fmt.Errorf("server error during shutdown: %v", err)
			}
		case <-shutdownCtx.Done():
			slog.Warn(fmt.Sprintf("%s server did not stop gracefully within timeout", transportName))
		}
	}
	return nil
}

func run(transport, addr, endpointPath string, logLevel slog.Level, dt disabledTools, config mcpcmdzero.CmdZeroConfig) error {
	slog.SetDefault(slog.New(slog.NewTextHandler(os.Stderr, &slog.HandlerOptions{Level: logLevel})))
	s := newServer(dt)

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, os.Interrupt, syscall.SIGTERM)
	defer signal.Stop(sigChan)

	go func() {
		<-sigChan
		slog.Info("Received shutdown signal")
		cancel()
		if transport == "stdio" {
			_ = os.Stdin.Close()
		}
	}()

	switch transport {
	case "stdio":
		srv := server.NewStdioServer(s)
		srv.SetContextFunc(mcpcmdzero.ComposedStdioContextFunc(config))
		slog.Info("Starting Command Zero MCP server using stdio transport", "version", mcpcmdzero.Version())
		err := srv.Listen(ctx, os.Stdin, os.Stdout)
		if err != nil && err != context.Canceled {
			return fmt.Errorf("server error: %v", err)
		}
		return nil

	case "streamable-http":
		opts := []server.StreamableHTTPOption{
			server.WithHTTPContextFunc(mcpcmdzero.ComposedHTTPContextFunc(config)),
			server.WithStateLess(true),
			server.WithEndpointPath(endpointPath),
		}
		srv := server.NewStreamableHTTPServer(s, opts...)
		slog.Info("Starting Command Zero MCP server using StreamableHTTP transport",
			"version", mcpcmdzero.Version(), "address", addr, "endpointPath", endpointPath)
		return runHTTPServer(ctx, srv, addr, "StreamableHTTP")

	default:
		return fmt.Errorf("invalid transport type: %s. Must be 'stdio' or 'streamable-http'", transport)
	}
}

func main() {
	var transport string
	flag.StringVar(&transport, "t", "stdio", "Transport type (stdio or streamable-http)")
	flag.StringVar(&transport, "transport", "stdio", "Transport type (stdio or streamable-http)")
	addr := flag.String("address", "localhost:8080", "Address for streamable-http server")
	endpointPath := flag.String("endpoint-path", "/mcp", "Endpoint path for streamable-http server")
	logLevel := flag.String("log-level", "info", "Log level (debug, info, warn, error)")
	showVersion := flag.Bool("version", false, "Print version and exit")

	var dt disabledTools
	dt.addFlags()
	flag.Parse()

	if *showVersion {
		fmt.Println(mcpcmdzero.Version())
		os.Exit(0)
	}

	config := mcpcmdzero.CmdZeroConfig{}

	if err := run(transport, *addr, *endpointPath, parseLevel(*logLevel), dt, config); err != nil {
		fmt.Fprintf(os.Stderr, "error: %v\n", err)
		os.Exit(1)
	}
}

func parseLevel(level string) slog.Level {
	var l slog.Level
	if err := l.UnmarshalText([]byte(level)); err != nil {
		return slog.LevelInfo
	}
	return l
}
