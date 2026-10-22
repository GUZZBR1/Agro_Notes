<?php

declare(strict_types=1);

namespace Drupal\farm_setup;

/**
 * Setup wizard logic.
 */
interface SetupWizardInterface {

  /**
   * Get the next setup form plugin ID.
   *
   * @param string $plugin_id
   *   The current setup form plugin ID.
   *
   * @return string|null
   *   The next setup form plugin ID, or NULL if there is none.
   */
  public function getNextPluginId(string $plugin_id): ?string;

  /**
   * Get the current block setup form plugin ID.
   *
   * @return string|null
   *   A setup form plugin ID, or NULL if setup has been completed.
   */
  public function getBlockPluginId(): ?string;

  /**
   * Set the current block setup form plugin ID.
   *
   * @param string|null $plugin_id
   *   A setup form plugin ID, or NULL to indicate setup has been completed.
   */
  public function setBlockPluginId(?string $plugin_id): void;

}
