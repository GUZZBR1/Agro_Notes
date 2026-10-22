<?php

declare(strict_types=1);

namespace Drupal\farm_setup;

use Drupal\Core\DependencyInjection\AutowireTrait;
use Drupal\Core\State\StateInterface;
use Symfony\Component\DependencyInjection\Attribute\Autowire;

/**
 * Setup wizard logic.
 */
class SetupWizard implements SetupWizardInterface {

  use AutowireTrait;

  public function __construct(
    #[Autowire(service: 'plugin.manager.setup_form')]
    protected SetupFormPluginManager $setupFormPluginManager,
    protected StateInterface $state,
  ) {}

  /**
   * {@inheritdoc}
   */
  public function getNextPluginId(string $plugin_id): ?string {
    $plugins = $this->setupFormPluginManager->getDefinitions();
    $keys = array_keys($plugins);
    $index = array_search($plugin_id, $keys);
    if ($index !== FALSE && isset($keys[$index + 1])) {
      return $keys[$index + 1];
    }
    return NULL;
  }

  /**
   * {@inheritdoc}
   */
  public function getBlockPluginId(): ?string {
    return $this->state->get('farm_setup.block');
  }

  /**
   * {@inheritdoc}
   */
  public function setBlockPluginId(?string $plugin_id): void {
    $this->state->set('farm_setup.block', $plugin_id);
  }

}
