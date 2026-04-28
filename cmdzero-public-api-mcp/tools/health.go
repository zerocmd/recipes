package tools

import (
	"context"
	"encoding/json"
	"fmt"

	"github.com/mark3labs/mcp-go/mcp"
	"github.com/mark3labs/mcp-go/server"

	mcpcmdzero "github.com/cmdzero/cmdzero-public-api-mcp"
)

// CheckHealthParams defines the parameters for the health check (none required).
type CheckHealthParams struct{}

func checkHealth(ctx context.Context, _ CheckHealthParams) (json.RawMessage, error) {
	c := mcpcmdzero.CmdZeroClientFromContext(ctx)
	if c == nil {
		return nil, fmt.Errorf("cmdzero client not configured")
	}

	return c.GetGlobal(ctx, "/ok")
}

var CheckHealth = mcpcmdzero.MustTool(
	"check_health",
	"Check Command Zero API health and authentication. Returns 200 OK if the API key is valid and the service is operational.",
	checkHealth,
	mcp.WithTitleAnnotation("Check API health"),
	mcp.WithIdempotentHintAnnotation(true),
	mcp.WithReadOnlyHintAnnotation(true),
)

// AddHealthTools registers all health tools with the server.
func AddHealthTools(s *server.MCPServer) {
	CheckHealth.Register(s)
}
