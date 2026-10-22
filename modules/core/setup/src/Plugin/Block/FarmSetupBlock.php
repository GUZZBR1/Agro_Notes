<?php

declare(strict_types=1);

namespace Drupal\farm_setup\Plugin\Block;

use Drupal\Core\Access\AccessResult;
use Drupal\Core\Block\Attribute\Block;
use Drupal\Core\Block\BlockBase;
use Drupal\Core\Form\FormBuilderInterface;
use Drupal\Core\Plugin\ContainerFactoryPluginInterface;
use Drupal\Core\Session\AccountInterface;
use Drupal\Core\StringTranslation\TranslatableMarkup;
use Drupal\farm_setup\Form\FarmSetupBlockForm;
use Drupal\farm_setup\SetupFormPluginManager;
use Drupal\farm_setup\SetupWizardInterface;
use Symfony\Component\DependencyInjection\Attribute\Autowire;
use Symfony\Component\DependencyInjection\ContainerInterface;

/**
 * Provides a farmOS setup block.
 */
#[Block(
  id: 'farm_setup',
  admin_label: new TranslatableMarkup('farmOS setup wizard'),
)]
class FarmSetupBlock extends BlockBase implements ContainerFactoryPluginInterface {

  public function __construct(
    array $configuration,
    $plugin_id,
    $plugin_definition,
    #[Autowire(service: 'plugin.manager.setup_form')]
    protected SetupFormPluginManager $setupFormPluginManager,
    protected SetupWizardInterface $setupWizard,
    protected FormBuilderInterface $formBuilder,
    protected AccountInterface $account,
  ) {
    parent::__construct($configuration, $plugin_id, $plugin_definition);
  }

  /**
   * {@inheritdoc}
   */
  public static function create(ContainerInterface $container, array $configuration, $plugin_id, $plugin_definition) {
    return new static(
      $configuration,
      $plugin_id,
      $plugin_definition,
      $container->get('plugin.manager.setup_form'),
      $container->get('farm_setup.wizard'),
      $container->get('form_builder'),
      $container->get('current_user'),
    );
  }

  /**
   * {@inheritdoc}
   */
  public function blockAccess(AccountInterface $account) {
    return AccessResult::allowedIfHasPermission($account, 'access farm setup wizard');
  }

  /**
   * {@inheritdoc}
   */
  public function build() {
    $build = [];

    // Get all setup form plugins.
    $plugins = $this->setupFormPluginManager->getDefinitions();

    // Get the next accessible plugin ID.
    $plugin_id = $this->getAccessiblePluginId();

    // If the current setup form plugin ID is NULL, or if it does not exist,
    // then consider the setup process to be complete and show nothing.
    if (is_null($plugin_id) || !array_key_exists($plugin_id, $plugins)) {
      return [];
    }

    // Instantiate the plugin.
    /** @var \Drupal\farm_setup\Plugin\SetupForm\SetupFormInterface $plugin */
    $plugin = $this->setupFormPluginManager->createInstance($plugin_id);

    // Show a progress bar (only include plugins the user has access to).
    $accessible_plugins = array_filter($plugins, function ($plugin) {
      return $this->setupFormPluginManager->createInstance($plugin['id'])->access($this->account)->isAllowed();
    });
    $step_count = count($accessible_plugins) - 1;
    $step_number = array_search($plugin_id, array_keys($accessible_plugins));
    $step_progress = round(($step_number / $step_count) * 100);
    $build['progress'] = [
      '#theme' => 'progress_bar',
      '#label' => $this->t('Setup progress'),
      '#percent' => $step_progress,
      '#message' => $this->t('Step @step_number: @step_label', ['@step_number' => $step_number + 1, '@step_label' => $plugin->getTaskTitle()]),
    ];

    // Build the setup form.
    $build['form'] = [
      '#type' => 'details',
      '#title' => $plugin->getTitle(),
      '#description' => $plugin->getDescription(),
      '#open' => TRUE,
      'form' => $this->formBuilder->getForm(FarmSetupBlockForm::class, $plugin_id),
    ];

    return $build;
  }

  /**
   * Get the next accessible plugin ID.
   *
   * @param string|null $plugin_id
   *   Optionally provide the current plugin ID. If this is omitted, it will be
   *   loaded from state.
   *
   * @return string|null
   *   A plugin ID.
   */
  protected function getAccessiblePluginId(?string $plugin_id = NULL): ?string {

    // Get the current plugin ID from state, if necessary.
    if (is_null($plugin_id)) {
      $plugin_id = $this->setupWizard->getBlockPluginId();
    }

    // If the user does not have access to the plugin, look up the next one that
    // they do have access to.
    $plugins = $this->setupFormPluginManager->getDefinitions();
    if (!is_null($plugin_id) && array_key_exists($plugin_id, $plugins) && !$this->setupFormPluginManager->createInstance($plugin_id)->access($this->account)->isAllowed()) {
      $plugin_id = $this->getAccessiblePluginId($this->setupWizard->getNextPluginId($plugin_id));
    }
    return $plugin_id;
  }

}
